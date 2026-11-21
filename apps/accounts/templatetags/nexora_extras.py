"""Small template helpers used across the NEXORA interface."""

from django import template
from django.utils import timezone

from apps.accounts.permissions import user_has_perm
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


def _date_format(context, fallback="d M Y"):
    user = context.get("current_user")
    if user is not None:
        try:
            return user.preferences().date_format
        except Exception:  # pragma: no cover - defensive
            return fallback
    return fallback


@register.simple_tag(takes_context=True)
def nx_date(context, value, fmt=None):
    if not value:
        return mark_safe('<span class="nx-muted">—</span>')
    if isinstance(value, str):
        return escape(value)
    fmt = fmt or _date_format(context)
    if hasattr(value, "hour"):
        value = timezone.localtime(value) if timezone.is_aware(value) else value
    return escape(value.strftime(fmt))


@register.simple_tag(takes_context=True)
def nx_datetime(context, value):
    if not value:
        return mark_safe('<span class="nx-muted">—</span>')
    fmt = _date_format(context)
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return escape(value.strftime(f"{fmt} · %H:%M"))


@register.simple_tag(takes_context=True)
def nx_time(context, value):
    if not value:
        return "—"
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return escape(value.strftime("%H:%M"))


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Build a querystring that keeps the current filters and page."""
    request = context.get("request")
    if request is None:
        return "?"
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"


@register.filter
def initials(name):
    if not name:
        return "—"
    parts = [part for part in str(name).split() if part]
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def has_perm(user, code):
    """Template-side RBAC check: ``{% if current_user|has_perm:"contacts.add" %}``."""
    return user_has_perm(user, code)


@register.filter
def elided_pages(page_obj, on_each_side=1, on_ends=1):
    """Page numbers around the current page for the pagination widget."""
    try:
        return page_obj.paginator.get_elided_page_range(
            page_obj.number, on_each_side=on_each_side, on_ends=on_ends
        )
    except Exception:  # pragma: no cover - defensive
        return [page_obj.number]


@register.filter
def category_tone(name):
    """Stable badge tone for a category name."""
    mapping = {
        "client": "sage",
        "supplier": "amber",
        "partner": "forest",
        "lead": "outline",
    }
    key = (name or "").strip().lower()
    if key in mapping:
        return mapping[key]
    tones = ["sage", "amber", "forest", "muted"]
    return tones[sum(ord(char) for char in key) % len(tones)]


@register.filter
def percent(part, total):
    try:
        part, total = float(part), float(total)
        if total <= 0:
            return 0
        return round((part / total) * 100)
    except (TypeError, ValueError):
        return 0


@register.filter
def mask_email(value):
    if not value or "@" not in str(value):
        return value
    local, domain = str(value).split("@", 1)
    visible = local[:2]
    return f"{visible}{'•' * max(len(local) - 2, 2)}@{domain}"


@register.filter
def dict_get(mapping, key):
    if hasattr(mapping, "get"):
        return mapping.get(key)
    return None
