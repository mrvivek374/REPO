"""Contact directory, contact profile and category management."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.permissions import permission_required

from .forms import CategoryForm, ContactForm
from .models import Category, Contact

SORT_OPTIONS = {
    "recent": ("Newest first", "-created_at"),
    "oldest": ("Oldest first", "created_at"),
    "name_asc": ("Name A → Z", "name"),
    "name_desc": ("Name Z → A", "-name"),
    "company": ("Company A → Z", "company"),
}


@permission_required("contacts.view")
def contact_list(request):
    contacts = Contact.objects.select_related("category", "created_by").annotate(
        interaction_total=Count("interactions", distinct=True),
        followup_total=Count("followups", distinct=True),
        last_contact=Max("interactions__interaction_date"),
    )

    q = request.GET.get("q", "").strip()
    search_field = request.GET.get("field", "all").strip().lower()
    category_filter = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "recent")
    view_mode = request.GET.get("view", "grid")

    # Specific query params if submitted individually
    name_q = request.GET.get("name", "").strip()
    company_q = request.GET.get("company", "").strip()
    email_q = request.GET.get("email", "").strip()
    phone_q = request.GET.get("phone", "").strip()

    if q:
        if search_field == "name":
            contacts = contacts.filter(name__icontains=q)
        elif search_field == "company":
            contacts = contacts.filter(company__icontains=q)
        elif search_field == "email":
            contacts = contacts.filter(email__icontains=q)
        elif search_field == "phone":
            contacts = contacts.filter(phone__icontains=q)
        else:
            contacts = contacts.filter(
                Q(name__icontains=q)
                | Q(company__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(job_title__icontains=q)
            )

    if name_q:
        contacts = contacts.filter(name__icontains=name_q)
    if company_q:
        contacts = contacts.filter(company__icontains=company_q)
    if email_q:
        contacts = contacts.filter(email__icontains=email_q)
    if phone_q:
        contacts = contacts.filter(phone__icontains=phone_q)

    if category_filter.isdigit():
        contacts = contacts.filter(category_id=int(category_filter))

    sort_label, sort_field = SORT_OPTIONS.get(sort, SORT_OPTIONS["recent"])
    contacts = contacts.order_by(sort_field, "contact_id")

    per_page = request.user.preferences().items_per_page
    page_obj = Paginator(contacts, per_page).get_page(request.GET.get("page"))

    return render(
        request,
        "contacts/list.html",
        {
            "page_obj": page_obj,
            "categories": Category.objects.annotate(total=Count("contacts")),
            "q": q,
            "search_field": search_field,
            "name_q": name_q,
            "company_q": company_q,
            "email_q": email_q,
            "phone_q": phone_q,
            "category_filter": category_filter,
            "sort": sort,
            "sort_options": SORT_OPTIONS,
            "sort_label": sort_label,
            "view_mode": view_mode,
            "total_contacts": Contact.objects.count(),
            "filtered_total": page_obj.paginator.count,
            "total_categories": Category.objects.count(),
            "active_total": Contact.objects.filter(
                interactions__interaction_date__gte=timezone.now() - timezone.timedelta(days=90)
            )
            .distinct()
            .count(),
            "page_title": "Contact Directory",
            "page_subtitle": "Every client, supplier, partner and lead in one place.",
            "breadcrumbs": [("Contacts", None)],
        },
    )


@permission_required("contacts.view")
def contact_detail(request, contact_id):
    contact = get_object_or_404(
        Contact.objects.select_related("category", "created_by"), pk=contact_id
    )
    interactions = contact.interactions.select_related("user").order_by("-interaction_date")
    followups = contact.followups.select_related("assigned_to").order_by("-due_date")
    open_followups = followups.filter(status="pending")
    overdue_followups = open_followups.filter(due_date__lt=timezone.now())

    return render(
        request,
        "contacts/detail.html",
        {
            "contact": contact,
            "interactions": interactions,
            "followups": followups,
            "open_followup_count": open_followups.count(),
            "overdue_followup_count": overdue_followups.count(),
            "last_interaction": interactions.first(),
            "page_title": contact.name,
            "page_subtitle": contact.company or "Contact profile",
            "breadcrumbs": [
                ("Directory", reverse("contacts:list")),
                (contact.name, None),
            ],
        },
    )


@permission_required("contacts.add")
def contact_create(request):
    form = ContactForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        contact = form.save(commit=False)
        contact.created_by = request.user
        contact.save()
        messages.success(
            request, f"{contact.name} was added to the directory as {contact.reference}."
        )
        return redirect("contacts:detail", contact_id=contact.contact_id)

    return render(
        request,
        "contacts/form.html",
        {
            "form": form,
            "mode": "create",
            "page_title": "Add Contact",
            "page_subtitle": "Create a new record in the NEXORA directory.",
            "breadcrumbs": [
                ("Directory", reverse("contacts:list")),
                ("Add contact", None),
            ],
        },
    )


@permission_required("contacts.edit")
def contact_edit(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    form = ContactForm(request.POST if request.method == "POST" else None, instance=contact)

    if request.method == "POST" and form.is_valid():
        contact = form.save()
        messages.success(request, f"{contact.name}'s details were updated.")
        return redirect("contacts:detail", contact_id=contact.contact_id)

    return render(
        request,
        "contacts/form.html",
        {
            "form": form,
            "mode": "edit",
            "contact": contact,
            "page_title": f"Edit {contact.name}",
            "page_subtitle": contact.company,
            "breadcrumbs": [
                ("Directory", reverse("contacts:list")),
                (contact.name, reverse("contacts:detail", args=[contact.contact_id])),
                ("Edit", None),
            ],
        },
    )


@require_POST
@permission_required("contacts.delete")
def contact_delete(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    name = contact.name
    contact.delete()
    messages.success(request, f"{name} and their history were deleted.")
    return redirect("contacts:list")


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@permission_required("categories.view")
def category_list(request):
    categories = Category.objects.annotate(total=Count("contacts")).order_by("category_name")
    form = CategoryForm()
    total_contacts = Contact.objects.count()

    return render(
        request,
        "contacts/categories.html",
        {
            "categories": categories,
            "form": form,
            "total_contacts": total_contacts,
            "page_title": "Categories",
            "page_subtitle": "Group contacts so reporting stays meaningful.",
            "breadcrumbs": [("Directory", reverse("contacts:list")), ("Categories", None)],
        },
    )


@require_POST
@permission_required("categories.manage")
def category_create(request):
    form = CategoryForm(request.POST)
    if form.is_valid():
        category = form.save()
        messages.success(request, f"Category “{category.category_name}” created.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    return redirect("contacts:category_list")


@permission_required("categories.manage")
def category_edit(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    form = CategoryForm(request.POST if request.method == "POST" else None, instance=category)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Category updated.")
        return redirect("contacts:category_list")

    return render(
        request,
        "contacts/category_form.html",
        {
            "form": form,
            "category": category,
            "page_title": f"Edit {category.category_name}",
            "breadcrumbs": [
                ("Categories", reverse("contacts:category_list")),
                (category.category_name, None),
            ],
        },
    )


@require_POST
@permission_required("categories.manage")
def category_delete(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    name = category.category_name
    try:
        category.delete()
        messages.success(request, f"Category “{name}” deleted.")
    except ProtectedError:
        count = category.contacts.count()
        messages.error(
            request,
            f"“{name}” is still used by {count} contact{'s' if count != 1 else ''}. "
            "Move those contacts to another category first.",
        )
    return redirect("contacts:category_list")
