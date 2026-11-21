"""NEXORA root URL configuration."""

from django.urls import include, path

from apps.accounts import views as account_views
from apps.reports import views as report_views

urlpatterns = [
    path("", account_views.root_redirect, name="root"),
    path("dashboard/", report_views.dashboard, name="dashboard"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.contacts.urls")),
    path("", include("apps.interactions.urls")),
    path("", include("apps.followups.urls")),
    path("", include("apps.reports.urls")),
]

handler403 = "apps.accounts.views.error_403"
handler404 = "apps.accounts.views.error_404"
