from django.urls import path

from . import views

app_name = "followups"

urlpatterns = [
    path("follow-ups/", views.followup_list, name="list"),
    path("follow-ups/add/", views.followup_create, name="create"),
    path("follow-ups/<int:followup_id>/edit/", views.followup_edit, name="edit"),
    path("follow-ups/<int:followup_id>/complete/", views.followup_complete, name="complete"),
    path("follow-ups/<int:followup_id>/reopen/", views.followup_reopen, name="reopen"),
    path("follow-ups/<int:followup_id>/delete/", views.followup_delete, name="delete"),
]
