"""Template context shared by every NEXORA page."""

from django.conf import settings
from django.utils import timezone

from apps.accounts.permissions import user_has_perm


def nexora_context(request):
    user = getattr(request, "user", None)
    logged_in = bool(user and getattr(user, "is_authenticated", False))

    context = {
        "nexora": settings.NEXORA,
        "current_user": user if logged_in else None,
        "can": (lambda code: user_has_perm(user, code)) if logged_in else (lambda code: False),
        "app_version": settings.NEXORA["VERSION"],
        "nav_overdue": 0,
        "nav_pending": 0,
        "nav_unread": 0,
    }

    if logged_in:
        from apps.followups.models import FollowUp

        pending = FollowUp.objects.filter(status=FollowUp.STATUS_PENDING)
        if getattr(user.role, "role_key", "") == "staff":
            pending = pending.filter(assigned_to=user)
        context["nav_pending"] = pending.count()
        context["nav_overdue"] = pending.filter(due_date__lt=timezone.now()).count()

    return context
