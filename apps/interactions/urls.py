from django.urls import path

from . import views

app_name = "interactions"

urlpatterns = [
    path("interactions/", views.interaction_list, name="list"),
    path("interactions/add/", views.interaction_create, name="create"),
    path("interactions/<int:interaction_id>/delete/", views.interaction_delete, name="delete"),
]
