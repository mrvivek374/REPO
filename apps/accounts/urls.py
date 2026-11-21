from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_view, name="profile"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/password/", views.password_change_view, name="password_change"),
    # User management (administrators only)
    path("team/", views.user_list, name="user_list"),
    path("team/add/", views.user_create, name="user_create"),
    path("team/<int:user_id>/edit/", views.user_edit, name="user_edit"),
    path("team/<int:user_id>/status/", views.user_toggle_status, name="user_toggle_status"),
    path("team/<int:user_id>/delete/", views.user_delete, name="user_delete"),
    path("team/roles/", views.role_list, name="role_list"),
    path("team/roles/<int:role_id>/", views.role_edit, name="role_edit"),
]
