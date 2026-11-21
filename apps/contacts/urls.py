from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [
    path("contacts/", views.contact_list, name="list"),
    path("contacts/add/", views.contact_create, name="create"),
    path("contacts/<int:contact_id>/", views.contact_detail, name="detail"),
    path("contacts/<int:contact_id>/edit/", views.contact_edit, name="edit"),
    path("contacts/<int:contact_id>/delete/", views.contact_delete, name="delete"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_create"),
    path("categories/<int:category_id>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:category_id>/delete/", views.category_delete, name="category_delete"),
]
