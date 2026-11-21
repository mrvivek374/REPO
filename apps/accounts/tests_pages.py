"""Smoke tests: every page renders without a template or server error."""

from django.test import TestCase
from django.urls import reverse

from apps.contacts.models import Category

from .testing import (
    PASSWORD,
    build_world,
    make_contact,
    make_followup,
    make_interaction,
)


class AdminPageRenderTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.contact = make_contact(self.world)
        self.interaction = make_interaction(self.world, self.contact)
        self.followup = make_followup(self.world, self.contact)
        self.client.login(username="admin", password=PASSWORD)

    def test_every_admin_page_renders(self):
        pages = [
            reverse("dashboard"),
            reverse("contacts:list"),
            reverse("contacts:list") + "?q=meridian&category=1&sort=name_asc&page=1",
            reverse("contacts:create"),
            reverse("contacts:detail", args=[self.contact.contact_id]),
            reverse("contacts:edit", args=[self.contact.contact_id]),
            reverse("contacts:category_list"),
            reverse("contacts:category_edit", args=[self.contact.category_id]),
            reverse("interactions:list"),
            reverse("interactions:create") + f"?contact={self.contact.contact_id}",
            reverse("followups:list"),
            reverse("followups:list") + "?tab=overdue",
            reverse("followups:list") + "?tab=completed",
            reverse("followups:list") + "?tab=all&q=quotation&assignee=1",
            reverse("followups:create"),
            reverse("followups:edit", args=[self.followup.followup_id]),
            reverse("reports:reports"),
            reverse("reports:reports") + "?start=2026-01-01&end=2026-12-31",
            reverse("accounts:user_list"),
            reverse("accounts:user_create"),
            reverse("accounts:user_edit", args=[self.world["staff"].pk]),
            reverse("accounts:role_list"),
            reverse("accounts:role_edit", args=[self.world["staff"].role_id]),
            reverse("accounts:profile"),
            reverse("accounts:settings"),
            reverse("accounts:password_change"),
        ]
        for url in pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, msg=f"{url} returned {response.status_code}")

    def test_administrator_role_edit_redirects_with_notice(self):
        response = self.client.get(
            reverse("accounts:role_edit", args=[self.world["roles"]["admin"].role_id]),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be edited")

    def test_edit_pages_render_bound_forms(self):
        response = self.client.get(reverse("contacts:edit", args=[self.contact.contact_id]))
        self.assertContains(response, self.contact.name)
        response = self.client.get(reverse("followups:edit", args=[self.followup.followup_id]))
        self.assertContains(response, "Edit Follow-up")


class StaffPageRenderTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.contact = make_contact(self.world)
        make_followup(self.world, self.contact, assignee="staff")
        make_interaction(self.world, self.contact)
        self.client.login(username="staff", password=PASSWORD)

    def test_staff_pages_render_and_restricted_pages_deny(self):
        allowed = [
            reverse("dashboard"),
            reverse("contacts:list"),
            reverse("contacts:create"),
            reverse("contacts:detail", args=[self.contact.contact_id]),
            reverse("contacts:category_list"),
            reverse("interactions:list"),
            reverse("interactions:create"),
            reverse("followups:list"),
            reverse("followups:create"),
            reverse("accounts:profile"),
            reverse("accounts:settings"),
        ]
        for url in allowed:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200, msg=url)

        denied = [
            reverse("reports:reports"),
            reverse("accounts:user_list"),
            reverse("accounts:role_list"),
            reverse("accounts:user_create"),
        ]
        for url in denied:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403, msg=url)

    def test_sidebar_hides_restricted_links(self):
        response = self.client.get(reverse("dashboard"))
        self.assertNotContains(response, "User Management")
        self.assertNotContains(response, "Reports &amp; Analytics")
        self.assertContains(response, "Follow-ups")


class EmptyStateRenderTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.client.login(username="admin", password=PASSWORD)

    def test_pages_render_with_no_records(self):
        pages = [
            reverse("dashboard"),
            reverse("contacts:list"),
            reverse("contacts:category_list"),
            reverse("interactions:list"),
            reverse("followups:list"),
            reverse("reports:reports"),
            reverse("accounts:user_list"),
        ]
        for url in pages:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200, msg=url)

    def test_category_create_rejects_duplicate(self):
        before = Category.objects.count()
        self.client.post(reverse("contacts:category_create"), {"category_name": "client"})
        self.assertEqual(Category.objects.count(), before)
