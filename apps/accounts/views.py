"""Authentication, user administration, profile and settings."""

from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, ProtectedError, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    LoginForm,
    NexoraPasswordChangeForm,
    PreferencesForm,
    ProfileForm,
    RolePermissionsForm,
    UserCreateForm,
    UserEditForm,
)
from .models import Role, User, UserPreference
from .permissions import permission_groups, permission_required


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("accounts:login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request=request, data=request.POST if request.method == "POST" else None)

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            user.preferences()  # make sure settings exist for the session
            if form.cleaned_data.get("remember"):
                request.session.set_expiry(60 * 60 * 24 * 14)  # 14 days
            else:
                request.session.set_expiry(0)  # until the browser closes
            messages.success(request, f"Welcome back, {user.get_short_name()}.")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return HttpResponseRedirect(next_url)
            return redirect("dashboard")
        messages.error(request, "We could not sign you in. Please check the details below.")

    return render(
        request,
        "accounts/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been signed out securely.")
    return redirect("accounts:login")


# ---------------------------------------------------------------------------
# Profile & settings
# ---------------------------------------------------------------------------
@login_required
def profile_view(request):
    user = request.user
    form = ProfileForm(request.POST if request.method == "POST" else None, instance=user)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")

    stats = {
        "contacts_created": user.contacts_created.count(),
        "interactions": user.interactions.count(),
        "followups_open": user.followups_assigned.filter(status="pending").count(),
        "followups_done": user.followups_assigned.filter(status="completed").count(),
    }
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "profile_stats": stats, "page_title": "My Profile"},
    )


@login_required
def settings_view(request):
    prefs = request.user.preferences()
    form = PreferencesForm(request.POST if request.method == "POST" else None, instance=prefs)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Application settings saved.")
            return redirect("accounts:settings")
        messages.error(request, "Please correct the highlighted settings.")

    return render(
        request,
        "accounts/settings.html",
        {
            "form": form,
            "page_title": "Settings",
            "page_subtitle": "Application preferences and account security.",
        },
    )


@login_required
def password_change_view(request):
    form = NexoraPasswordChangeForm(user=request.user, data=request.POST if request.method == "POST" else None)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Your password has been changed. Keep it safe.")
            return redirect("accounts:settings")
        messages.error(request, "Your password could not be changed. See the notes below.")

    return render(
        request,
        "accounts/password_change.html",
        {"form": form, "page_title": "Change Password"},
    )


# ---------------------------------------------------------------------------
# User management (administrator only)
# ---------------------------------------------------------------------------
@permission_required("users.manage")
def user_list(request):
    users = User.objects.select_related("role").annotate(
        contact_total=Count("contacts_created", distinct=True),
        followup_total=Count("followups_assigned", distinct=True),
    )

    q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        users = users.filter(
            Q(name__icontains=q) | Q(username__icontains=q) | Q(email__icontains=q)
        )
    if role_filter:
        users = users.filter(role__role_key=role_filter)
    if status_filter:
        users = users.filter(status=status_filter)

    users = users.order_by("name")
    per_page = request.user.preferences().items_per_page
    page_obj = Paginator(users, per_page).get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/user_list.html",
        {
            "page_obj": page_obj,
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(status=User.STATUS_ACTIVE).count(),
            "roles": Role.objects.annotate(user_total=Count("users")),
            "q": q,
            "role_filter": role_filter,
            "status_filter": status_filter,
            "page_title": "User Management",
            "page_subtitle": "Accounts, roles and access for your team.",
            "breadcrumbs": [("Team", None)],
        },
    )


@permission_required("users.manage")
def user_create(request):
    form = UserCreateForm(request.POST if request.method == "POST" else None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"{user.name} can now sign in as @{user.username}.")
        return redirect("accounts:user_list")

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "mode": "create",
            "page_title": "Add Team Member",
            "breadcrumbs": [("Team", reverse("accounts:user_list")), ("Add member", None)],
        },
    )


@permission_required("users.manage")
def user_edit(request, user_id):
    target = get_object_or_404(User.objects.select_related("role"), pk=user_id)
    form = UserEditForm(request.POST if request.method == "POST" else None, instance=target)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{target.name}'s account has been updated.")
        return redirect("accounts:user_list")

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "mode": "edit",
            "target": target,
            "page_title": "Edit Team Member",
            "breadcrumbs": [("Team", reverse("accounts:user_list")), (target.name, None)],
        },
    )


@require_POST
@permission_required("users.manage")
def user_toggle_status(request, user_id):
    target = get_object_or_404(User, pk=user_id)

    if target.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:user_list")

    if target.status == User.STATUS_ACTIVE:
        if target.role.role_key == "admin":
            remaining = (
                User.objects.filter(role__role_key="admin", status=User.STATUS_ACTIVE)
                .exclude(pk=target.pk)
                .count()
            )
            if remaining == 0:
                messages.error(request, "At least one active administrator must remain.")
                return redirect("accounts:user_list")
        target.status = User.STATUS_INACTIVE
        messages.success(request, f"{target.name} has been deactivated.")
    else:
        target.status = User.STATUS_ACTIVE
        messages.success(request, f"{target.name} has been reactivated.")

    target.save(update_fields=["status"])
    return redirect("accounts:user_list")


@require_POST
@permission_required("users.manage")
def user_delete(request, user_id):
    target = get_object_or_404(User, pk=user_id)

    if target.pk == request.user.pk:
        messages.error(request, "You cannot delete the account you are signed in with.")
        return redirect("accounts:user_list")

    if target.role.role_key == "admin" and not User.objects.filter(
        role__role_key="admin", status=User.STATUS_ACTIVE
    ).exclude(pk=target.pk).exists():
        messages.error(request, "At least one administrator must remain in the system.")
        return redirect("accounts:user_list")

    try:
        name = target.name
        target.delete()
        messages.success(request, f"{name}'s account has been removed.")
    except ProtectedError:
        messages.error(
            request,
            f"{target.name} is linked to contacts or records. "
            "Deactivate the account instead of deleting it.",
        )
    return redirect("accounts:user_list")


@permission_required("users.manage")
def role_list(request):
    roles = Role.objects.annotate(user_total=Count("users"))
    return render(
        request,
        "accounts/role_list.html",
        {
            "roles": roles,
            "groups": permission_groups(),
            "page_title": "Roles & Permissions",
            "breadcrumbs": [("Team", reverse("accounts:user_list")), ("Roles", None)],
        },
    )


@permission_required("users.manage")
def role_edit(request, role_id):
    role = get_object_or_404(Role, pk=role_id)
    form = RolePermissionsForm(request.POST if request.method == "POST" else None, role=role)

    if role.is_locked:
        messages.info(
            request,
            "The Administrator role always holds every permission and cannot be edited.",
        )
        return redirect("accounts:role_list")

    if request.method == "POST" and form.is_valid():
        role.permissions = form.selected_codes()
        role.save(update_fields=["permissions"])
        messages.success(request, f"{role.role_name} permissions updated.")
        return redirect("accounts:role_list")

    form_groups = [
        (
            group,
            [
                {"code": item["code"], "label": item["label"], "field": form[item["code"]]}
                for item in items
            ],
        )
        for group, items in permission_groups()
    ]

    return render(
        request,
        "accounts/role_form.html",
        {
            "role": role,
            "form": form,
            "groups": form_groups,
            "page_title": f"Permissions · {role.role_name}",
            "breadcrumbs": [
                ("Team", reverse("accounts:user_list")),
                ("Roles", reverse("accounts:role_list")),
                (role.role_name, None),
            ],
        },
    )


# ---------------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------------
def error_403(request, exception=None):
    return render(
        request,
        "errors/403.html",
        {"message": str(exception) if exception else "", "page_title": "Access denied"},
        status=403,
    )


def error_404(request, exception=None):
    return render(request, "errors/404.html", {"page_title": "Not found"}, status=404)
