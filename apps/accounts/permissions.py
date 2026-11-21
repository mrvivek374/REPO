"""Central catalogue of NEXORA permissions and the RBAC helpers.

Permissions live in the ``roles.permissions`` JSON column, so an
administrator can change what a role may do from the User Management
screen. Every server view is guarded by :func:`permission_required`,
which means hiding a navigation item is never the only protection.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

# code, human label, UI group
PERMISSIONS = [
    ("dashboard.view", "View the dashboard", "Workspace"),
    ("contacts.view", "View the contact directory", "Contacts"),
    ("contacts.add", "Add new contacts", "Contacts"),
    ("contacts.edit", "Edit existing contacts", "Contacts"),
    ("contacts.delete", "Delete contacts", "Contacts"),
    ("categories.view", "View categories", "Categories"),
    ("categories.manage", "Create, edit and delete categories", "Categories"),
    ("interactions.view", "View interaction history", "Interactions"),
    ("interactions.add", "Record interactions", "Interactions"),
    ("followups.view", "View follow-ups", "Follow-ups"),
    ("followups.add", "Create follow-ups", "Follow-ups"),
    ("followups.edit", "Update and complete follow-ups", "Follow-ups"),
    ("reports.view", "View reports and analytics", "Insights"),
    ("users.manage", "Manage users, roles and permissions", "Administration"),
]

ALL_PERMISSION_CODES = tuple(code for code, _label, _group in PERMISSIONS)


def permission_groups():
    """Return permissions grouped for the role editor UI."""
    groups, order = {}, []
    for code, label, group in PERMISSIONS:
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append({"code": code, "label": label})
    return [(group, groups[group]) for group in order]


ROLE_LABELS = {
    "admin": "Administrator",
    "manager": "Business Owner / Manager",
    "staff": "Staff / Employee",
}

ROLE_DESCRIPTIONS = {
    "admin": "Full system access: users, roles, contacts, categories, interactions, "
             "follow-ups and reports.",
    "manager": "Business oversight: dashboard, all contacts, interactions, follow-ups "
               "and full reporting. Cannot manage users or delete contacts.",
    "staff": "Day-to-day contact work: add and update contacts, record interactions and "
             "manage follow-ups assigned to them.",
}

# Initial permission sets. Administrators always hold every permission.
ROLE_PRESETS = {
    "admin": list(ALL_PERMISSION_CODES),
    "manager": [
        "dashboard.view",
        "contacts.view",
        "contacts.add",
        "contacts.edit",
        "categories.view",
        "interactions.view",
        "interactions.add",
        "followups.view",
        "followups.add",
        "followups.edit",
        "reports.view",
    ],
    "staff": [
        "dashboard.view",
        "contacts.view",
        "contacts.add",
        "contacts.edit",
        "categories.view",
        "interactions.view",
        "interactions.add",
        "followups.view",
        "followups.add",
        "followups.edit",
    ],
}


def user_has_perm(user, code):
    """True when the given user is allowed to perform ``code``."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "status", "") != "active":
        return False
    role = getattr(user, "role", None)
    if role is None:
        return False
    if role.role_key == "admin":  # administrators are never locked out
        return True
    return code in (role.permissions or [])


def permission_required(code, message=""):
    """Decorator enforcing a single permission on the server side."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not user_has_perm(request.user, code):
                raise PermissionDenied(
                    message
                    or "Your role does not include permission for this action. "
                    "Ask an administrator to update your access."
                )
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
