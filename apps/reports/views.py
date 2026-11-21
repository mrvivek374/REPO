"""Dashboard and reporting views."""

from datetime import datetime, timedelta

from django.shortcuts import render
from django.utils import timezone

from apps.accounts.permissions import permission_required
from apps.followups.models import FollowUp

from .services import (
    category_distribution,
    dashboard_stats,
    followup_status_chart,
    monthly_contact_growth,
    months_between,
    overdue_followup_list,
    recent_activities,
    recent_contacts,
    report_context,
    upcoming_followup_list,
)


def _greeting():
    hour = timezone.localtime().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@permission_required("dashboard.view")
def dashboard(request):
    stats = dashboard_stats()
    user = request.user
    my_open = FollowUp.objects.filter(assigned_to=user, status=FollowUp.STATUS_PENDING)
    my_overdue = my_open.filter(due_date__lt=timezone.now())

    context = {
        "stats": stats,
        "greeting": _greeting(),
        "today": timezone.localdate(),
        "activities": recent_activities(6),
        "recent_contacts": recent_contacts(5),
        "upcoming": upcoming_followup_list(4),
        "overdue": overdue_followup_list(4),
        "category_chart": category_distribution(),
        "status_chart": followup_status_chart(),
        "growth_chart": monthly_contact_growth(),
        "my_open_followups": my_open.count(),
        "my_overdue_followups": my_overdue.count(),
        "my_open_list": my_open.select_related("contact").order_by("due_date")[:3],
        "page_title": "Dashboard",
        "page_subtitle": "A live view of your relationship pipeline.",
        "is_dashboard": True,
    }
    return render(request, "dashboard.html", context)


def _parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@permission_required("reports.view")
def reports(request):
    today = timezone.localdate()
    start = _parse_date(request.GET.get("start", "").strip())
    end = _parse_date(request.GET.get("end", "").strip())

    if start is None:
        start = today.replace(day=1) - timedelta(days=180)
    if end is None:
        end = today
    if start > end:
        start, end = end, start

    context = report_context(start, end)
    context.update(
        {
            "start": start,
            "end": end,
            "start_raw": start.isoformat(),
            "end_raw": end.isoformat(),
            "range_label": f"{start:%d %b %Y} – {end:%d %b %Y}",
            "month_count": len(months_between(start, end)),
            "overdue_tasks": overdue_followup_list(6),
            "upcoming_tasks": upcoming_followup_list(6),
            "presets": [
                {
                    "label": "Last 30 days",
                    "start": (today - timedelta(days=29)).isoformat(),
                    "end": today.isoformat(),
                },
                {
                    "label": "Last 90 days",
                    "start": (today - timedelta(days=89)).isoformat(),
                    "end": today.isoformat(),
                },
                {
                    "label": "Last 6 months",
                    "start": (today - timedelta(days=181)).isoformat(),
                    "end": today.isoformat(),
                },
                {
                    "label": "This month",
                    "start": today.replace(day=1).isoformat(),
                    "end": today.isoformat(),
                },
            ],
            "page_title": "Reports & Analytics",
            "page_subtitle": "Understand growth, engagement and follow-through.",
            "breadcrumbs": [("Reports", None)],
        }
    )
    return render(request, "reports/index.html", context)
