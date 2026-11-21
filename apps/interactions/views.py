"""Recording and reviewing contact interactions."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.permissions import permission_required, user_has_perm
from apps.contacts.models import Contact

from .forms import InteractionForm
from .models import Interaction


@permission_required("interactions.view")
def interaction_list(request):
    interactions = Interaction.objects.select_related("contact", "user")

    q = request.GET.get("q", "").strip()
    type_filter = request.GET.get("type", "").strip()
    contact_filter = request.GET.get("contact", "").strip()

    if q:
        interactions = interactions.filter(
            Q(contact__name__icontains=q)
            | Q(contact__company__icontains=q)
            | Q(notes__icontains=q)
        )
    if type_filter:
        interactions = interactions.filter(interaction_type=type_filter)
    if contact_filter.isdigit():
        interactions = interactions.filter(contact_id=int(contact_filter))

    interactions = interactions.order_by("-interaction_date")
    per_page = request.user.preferences().items_per_page
    page_obj = Paginator(interactions, per_page).get_page(request.GET.get("page"))

    month_start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_total = Interaction.objects.filter(interaction_date__gte=month_start).count()

    return render(
        request,
        "interactions/list.html",
        {
            "page_obj": page_obj,
            "type_choices": Interaction.TYPE_CHOICES,
            "type_filter": type_filter,
            "contact_filter": contact_filter,
            "q": q,
            "contacts": Contact.objects.order_by("name"),
            "total_interactions": Interaction.objects.count(),
            "month_total": month_total,
            "page_title": "Interaction Timeline",
            "page_subtitle": "Every call, meeting and email recorded by your team.",
            "breadcrumbs": [("Interactions", None)],
        },
    )


@permission_required("interactions.add")
def interaction_create(request):
    contact = None
    contact_id = request.GET.get("contact")
    if contact_id and contact_id.isdigit():
        contact = Contact.objects.filter(pk=contact_id).first()
    if request.method == "POST" and request.POST.get("contact", "").isdigit():
        contact = Contact.objects.filter(pk=int(request.POST["contact"])).first()

    form = InteractionForm(request.POST if request.method == "POST" else None, contact=contact)

    if request.method == "POST" and form.is_valid():
        interaction = form.save(commit=False)
        interaction.user = request.user
        interaction.save()
        messages.success(
            request,
            f"{interaction.get_interaction_type_display()} with "
            f"{interaction.contact.name} added to the history.",
        )
        return redirect("contacts:detail", contact_id=interaction.contact_id)

    return render(
        request,
        "interactions/form.html",
        {
            "form": form,
            "contact": contact,
            "page_title": "Record Interaction",
            "page_subtitle": "Log what happened while it is still fresh.",
            "breadcrumbs": [
                ("Interactions", reverse("interactions:list")),
                ("Record", None),
            ],
        },
    )


@require_POST
@permission_required("interactions.add")
def interaction_delete(request, interaction_id):
    interaction = get_object_or_404(Interaction.objects.select_related("contact"), pk=interaction_id)
    if interaction.user_id != request.user.pk and not user_has_perm(request.user, "users.manage"):
        raise PermissionDenied("Only the person who recorded this interaction can delete it.")
    contact_id = interaction.contact_id
    interaction.delete()
    messages.success(request, "Interaction removed from the history.")
    return redirect("contacts:detail", contact_id=contact_id)
