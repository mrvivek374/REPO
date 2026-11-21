"""Database aggregation used by the dashboard and the reports page.

Nothing here is hard-coded: every number and chart point comes from the
ORM so the UI always reflects the stored records.

Date ranges are expressed as aware datetime bounds instead of ``__date``
lookups. That keeps the queries index-friendly and avoids MySQL's
``CONVERT_TZ`` dependency on a populated timezone table.
"""

from datetime import date, datetime, time as dtime, timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.contacts.models import Category, Contact
from apps.followups.models import FollowUp
from apps.interactions.models import Interaction


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def _bound(day: date, end_of_day: bool = False):
    moment = datetime.combine(day, dtime.max if end_of_day else dtime.min)
    return timezone.make_aware(moment) if settings.USE_TZ else moment


def _shift_month(day: date, delta: int) -> date:
    year, month = day.year, day.month + delta
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    return date(year, month, 1)


def months_between(start: date, end: date):
    current, last, months = start.replace(day=1), end.replace(day=1), []
    while current <= last and len(months) < 24:
        months.append(current)
        current = _shift_month(current, 1)
    return months


def _end_of_month(day: date) -> date:
    return _shift_month(day, 1) - timedelta(days=1)


def _apply_range(qs, field, start=None, end=None):
    if start:
        qs = qs.filter(**{f"{field}__gte": _bound(start)})
    if end:
        qs = qs.filter(**{f"{field}__lte": _bound(end, end_of_day=True)})
    return qs


def _localised(value):
    if value is None:
        return None
    return timezone.localtime(value) if timezone.is_aware(value) else value


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def monthly_contact_growth(months=6, start=None, end=None):
    """Contact creation totals per month, oldest month first."""
    today = timezone.localdate()
    if start and end and start <= end:
        keys = months_between(start, end)[-12:]
    else:
        keys = months_between(_shift_month(today, -(months - 1)), today)

    if not keys:
        return {"labels": [], "short_labels": [], "values": []}

    qs = Contact.objects.filter(
        created_at__gte=_bound(keys[0]),
        created_at__lte=_bound(_end_of_month(keys[-1]), end_of_day=True),
    )

    tally = {}
    for created_at in qs.values_list("created_at", flat=True):
        created_at = _localised(created_at)
        key = date(created_at.year, created_at.month, 1)
        tally[key] = tally.get(key, 0) + 1

    return {
        "labels": [month.strftime("%b %Y") for month in keys],
        "short_labels": [month.strftime("%b") for month in keys],
        "values": [tally.get(month, 0) for month in keys],
    }


def category_distribution(start=None, end=None):
    qs = _apply_range(Contact.objects.all(), "created_at", start, end)
    rows = (
        qs.values("category__category_name")
        .annotate(total=Count("contact_id"))
        .order_by("-total", "category__category_name")
    )
    return {
        "labels": [row["category__category_name"] or "Uncategorised" for row in rows],
        "values": [row["total"] for row in rows],
    }


def category_table(start=None, end=None):
    """Category rows with their share of the filtered contact total."""
    contacts = _apply_range(Contact.objects.all(), "created_at", start, end)
    total = contacts.count()

    rows = []
    for category in Category.objects.all():
        count = contacts.filter(category=category).count()
        rows.append(
            {
                "name": category.category_name,
                "description": category.description,
                "total": count,
                "share": round((count / total) * 100) if total else 0,
            }
        )
    rows.sort(key=lambda row: row["total"], reverse=True)
    return rows


def interaction_summary(start=None, end=None):
    qs = _apply_range(Interaction.objects.all(), "interaction_date", start, end)
    rows = qs.values("interaction_type").annotate(total=Count("interaction_id"))
    tally = {row["interaction_type"]: row["total"] for row in rows}

    labels, values = [], []
    for code, label in Interaction.TYPE_CHOICES:
        labels.append(label)
        values.append(tally.get(code, 0))
    return {"labels": labels, "values": values, "total": sum(values)}


def followup_summary(start=None, end=None):
    now = timezone.now()
    qs = _apply_range(FollowUp.objects.all(), "due_date", start, end)

    pending = qs.filter(status=FollowUp.STATUS_PENDING, due_date__gte=now).count()
    overdue = qs.filter(status=FollowUp.STATUS_PENDING, due_date__lt=now).count()
    completed = qs.filter(status=FollowUp.STATUS_COMPLETED).count()
    total = pending + overdue + completed

    return {
        "pending": pending,
        "overdue": overdue,
        "completed": completed,
        "total": total,
        "completion_rate": round((completed / total) * 100) if total else 0,
        "overdue_rate": round((overdue / total) * 100) if total else 0,
    }


def followup_status_chart(start=None, end=None):
    summary = followup_summary(start, end)
    return {
        "labels": ["Pending", "Overdue", "Completed"],
        "values": [summary["pending"], summary["overdue"], summary["completed"]],
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def dashboard_stats():
    now = timezone.now()
    today = timezone.localdate()
    month_start = today.replace(day=1)
    last_month_start = _shift_month(month_start, -1)
    active_cutoff = now - timedelta(days=90)

    total = Contact.objects.count()
    active_contacts = (
        Contact.objects.filter(interactions__interaction_date__gte=active_cutoff)
        .distinct()
        .count()
    )

    pending = FollowUp.objects.filter(status=FollowUp.STATUS_PENDING)
    upcoming_window = pending.filter(due_date__gte=now, due_date__lte=now + timedelta(days=7))
    overdue = pending.filter(due_date__lt=now)

    this_month_contacts = Contact.objects.filter(
        created_at__gte=_bound(month_start)
    ).count()
    last_month_contacts = Contact.objects.filter(
        created_at__gte=_bound(last_month_start), created_at__lt=_bound(month_start)
    ).count()

    if last_month_contacts:
        growth = round(((this_month_contacts - last_month_contacts) / last_month_contacts) * 100)
    else:
        growth = 100 if this_month_contacts else 0

    followups = followup_summary()

    return {
        "total_contacts": total,
        "active_contacts": active_contacts,
        "inactive_contacts": max(total - active_contacts, 0),
        "total_categories": Category.objects.count(),
        "total_interactions": Interaction.objects.count(),
        "interactions_this_month": Interaction.objects.filter(
            interaction_date__gte=_bound(month_start)
        ).count(),
        "pending_followups": pending.count(),
        "upcoming_followups": upcoming_window.count(),
        "overdue_followups": overdue.count(),
        "completed_followups": FollowUp.objects.filter(
            status=FollowUp.STATUS_COMPLETED
        ).count(),
        "this_month_contacts": this_month_contacts,
        "last_month_contacts": last_month_contacts,
        "month_growth": growth,
        "completion_rate": followups["completion_rate"],
        "followup_summary": followups,
    }


def recent_activities(limit=6):
    """Merge recent interactions and completed follow-ups into one feed."""
    activities = []

    for interaction in Interaction.objects.select_related("contact", "user").order_by(
        "-interaction_date"
    )[:limit]:
        activities.append(
            {
                "icon": interaction.icon,
                "tone": interaction.tone,
                "title": f"{interaction.get_interaction_type_display()} with "
                         f"{interaction.contact.name}",
                "meta": interaction.contact.company or interaction.contact.email,
                "actor": interaction.user.name,
                "when": interaction.interaction_date,
                "url": f"/contacts/{interaction.contact_id}/",
            }
        )

    for followup in (
        FollowUp.objects.select_related("contact", "assigned_to")
        .filter(status=FollowUp.STATUS_COMPLETED, completed_at__isnull=False)
        .order_by("-completed_at")[:4]
    ):
        activities.append(
            {
                "icon": "check",
                "tone": "success",
                "title": f"Follow-up completed with {followup.contact.name}",
                "meta": followup.contact.company or "Follow-up task",
                "actor": followup.assigned_to.name,
                "when": followup.completed_at,
                "url": f"/contacts/{followup.contact_id}/",
            }
        )

    activities.sort(key=lambda item: item["when"], reverse=True)
    return activities[:limit]


def recent_contacts(limit=5):
    return Contact.objects.select_related("category", "created_by").order_by("-created_at")[
        :limit
    ]


def upcoming_followup_list(limit=5):
    return (
        FollowUp.objects.select_related("contact", "assigned_to")
        .filter(status=FollowUp.STATUS_PENDING, due_date__gte=timezone.now())
        .order_by("due_date")[:limit]
    )


def overdue_followup_list(limit=5):
    return (
        FollowUp.objects.select_related("contact", "assigned_to")
        .filter(status=FollowUp.STATUS_PENDING, due_date__lt=timezone.now())
        .order_by("due_date")[:limit]
    )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def contributor_counts(contacts):
    rows = (
        contacts.values("created_by__name", "created_by__role__role_name")
        .annotate(total=Count("contact_id"))
        .order_by("-total")
    )
    return [
        {
            "name": row["created_by__name"],
            "role": row["created_by__role__role_name"] or "—",
            "total": row["total"],
        }
        for row in rows
    ]


def report_context(start=None, end=None):
    """Everything the reports page needs, already filtered."""
    contacts = _apply_range(Contact.objects.all(), "created_at", start, end)
    interactions = _apply_range(Interaction.objects.all(), "interaction_date", start, end)
    summary = followup_summary(start, end)

    return {
        "new_contacts": contacts.count(),
        "total_contacts": Contact.objects.count(),
        "interactions": interactions.count(),
        "interactions_by_type": interaction_summary(start, end),
        "followups": summary,
        "monthly": monthly_contact_growth(start=start, end=end),
        "distribution": category_distribution(start, end),
        "category_table": category_table(start, end),
        "status_chart": followup_status_chart(start, end),
        "contributors": contributor_counts(contacts),
    }
