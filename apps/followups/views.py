"""Follow-up tracking: upcoming, overdue, completed and task actions."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.accounts.permissions import permission_required, user_has_perm
from apps.contacts.models import Contact

from .forms import FollowUpForm
from .models import FollowUp

TABS = (
    ("upcoming", "Upcoming"),
    ("overdue", "Overdue"),
    ("completed", "Completed"),
    ("all", "All tasks"),
)


def scoped_followups(user):
    """Staff only work with their own tasks; managers and admins see everything."""
    qs = FollowUp.objects.select_related("contact", "assigned_to", "created_by")
    if user.role and user.role.role_key == "staff":
        return qs.filter(Q(assigned_to=user) | Q(created_by=user)).distinct()
    return qs


def safe_next(request, fallback="followups:list"):
    target = request.POST.get("next")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return reverse(fallback)


def can_manage(user, followup):
    if user.role and user.role.role_key in ("admin", "manager"):
        return True
    return followup.assigned_to_id == user.pk or followup.created_by_id == user.pk


@permission_required("followups.view")
def followup_list(request):
    now = timezone.now()
    scope = scoped_followups(request.user)

    tab = request.GET.get("tab", "upcoming")
    if tab not in dict(TABS):
        tab = "upcoming"

    q = request.GET.get("q", "").strip()
    assignee_filter = request.GET.get("assignee", "").strip()

    qs = scope
    if q:
        qs = qs.filter(
            Q(contact__name__icontains=q)
            | Q(contact__company__icontains=q)
            | Q(notes__icontains=q)
        )
    if assignee_filter.isdigit():
        qs = qs.filter(assigned_to_id=int(assignee_filter))

    if tab == "upcoming":
        qs = qs.filter(status=FollowUp.STATUS_PENDING, due_date__gte=now).order_by("due_date")
    elif tab == "overdue":
        qs = qs.filter(status=FollowUp.STATUS_PENDING, due_date__lt=now).order_by("due_date")
    elif tab == "completed":
        qs = qs.filter(status=FollowUp.STATUS_COMPLETED).order_by("-completed_at")
    else:
        qs = qs.order_by("status", "due_date")

    counts = {
        "upcoming": scope.filter(status=FollowUp.STATUS_PENDING, due_date__gte=now).count(),
        "overdue": scope.filter(status=FollowUp.STATUS_PENDING, due_date__lt=now).count(),
        "completed": scope.filter(status=FollowUp.STATUS_COMPLETED).count(),
        "all": scope.count(),
    }

    per_page = request.user.preferences().items_per_page
    page_obj = Paginator(qs, per_page).get_page(request.GET.get("page"))

    can_pick_assignee = request.user.role and request.user.role.role_key in ("admin", "manager")

    return render(
        request,
        "followups/list.html",
        {
            "page_obj": page_obj,
            "tabs": TABS,
            "active_tab": tab,
            "counts": counts,
            "q": q,
            "assignee_filter": assignee_filter,
            "assignees": User.objects.filter(status=User.STATUS_ACTIVE).order_by("name")
            if can_pick_assignee
            else User.objects.filter(pk=request.user.pk),
            "page_title": "Follow-ups",
            "page_subtitle": "Promises kept on time — with nothing slipping through.",
            "breadcrumbs": [("Follow-ups", None)],
        },
    )


@permission_required("followups.add")
def followup_create(request):
    contact = None
    contact_id = request.GET.get("contact")
    if contact_id and contact_id.isdigit():
        contact = Contact.objects.filter(pk=contact_id).first()

    restrict = not (request.user.role and request.user.role.role_key in ("admin", "manager"))
    form = FollowUpForm(
        request.POST if request.method == "POST" else None,
        contact=contact,
        acting_user=request.user,
        restrict_assignee=restrict,
    )

    if request.method == "POST" and form.is_valid():
        followup = form.save(commit=False)
        followup.created_by = request.user
        followup.status = FollowUp.STATUS_PENDING
        followup.save()
        messages.success(
            request,
            f"Follow-up with {followup.contact.name} scheduled for "
            f"{timezone.localtime(followup.due_date):%d %b %Y, %H:%M}.",
        )
        return redirect("followups:list")

    return render(
        request,
        "followups/form.html",
        {
            "form": form,
            "contact": contact,
            "mode": "create",
            "page_title": "New Follow-up",
            "page_subtitle": "Schedule the next touchpoint and assign an owner.",
            "breadcrumbs": [("Follow-ups", reverse("followups:list")), ("New", None)],
        },
    )


@permission_required("followups.edit")
def followup_edit(request, followup_id):
    followup = get_object_or_404(
        FollowUp.objects.select_related("contact"), pk=followup_id
    )
    if not can_manage(request.user, followup):
        raise PermissionDenied("This follow-up is assigned to another team member.")

    restrict = not (request.user.role and request.user.role.role_key in ("admin", "manager"))
    form = FollowUpForm(
        request.POST if request.method == "POST" else None,
        instance=followup,
        acting_user=request.user,
        restrict_assignee=restrict,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Follow-up updated.")
        return redirect("followups:list")

    return render(
        request,
        "followups/form.html",
        {
            "form": form,
            "followup": followup,
            "mode": "edit",
            "page_title": "Edit Follow-up",
            "page_subtitle": followup.contact.name,
            "breadcrumbs": [
                ("Follow-ups", reverse("followups:list")),
                (followup.contact.name, None),
            ],
        },
    )


@require_POST
@permission_required("followups.edit")
def followup_complete(request, followup_id):
    followup = get_object_or_404(FollowUp, pk=followup_id)
    if not can_manage(request.user, followup):
        raise PermissionDenied("This follow-up is assigned to another team member.")
    if followup.status == FollowUp.STATUS_COMPLETED:
        messages.info(request, "That follow-up is already complete.")
    else:
        followup.mark_completed()
        messages.success(request, f"Follow-up with {followup.contact.name} completed.")
    return redirect(safe_next(request))


@require_POST
@permission_required("followups.edit")
def followup_reopen(request, followup_id):
    followup = get_object_or_404(FollowUp, pk=followup_id)
    if not can_manage(request.user, followup):
        raise PermissionDenied("This follow-up is assigned to another team member.")
    followup.reopen()
    messages.info(request, "Follow-up reopened and set back to pending.")
    return redirect(safe_next(request))


@require_POST
@permission_required("followups.edit")
def followup_delete(request, followup_id):
    followup = get_object_or_404(FollowUp, pk=followup_id)
    if not can_manage(request.user, followup) or not user_has_perm(
        request.user, "followups.add"
    ):
        raise PermissionDenied("You cannot delete this follow-up.")
    name = followup.contact.name
    followup.delete()
    messages.success(request, f"Follow-up with {name} deleted.")
    return redirect(safe_next(request))
