"""Tests for the contact directory, validation and categories."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.testing import PASSWORD, build_world, make_contact, make_followup, make_interaction

from .models import Category, Contact


class ContactCrudTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.client.login(username="admin", password=PASSWORD)

    def payload(self, **overrides):
        data = {
            "name": "Aarav Mehta",
            "company": "Meridian Textiles",
            "job_title": "Procurement Lead",
            "phone": "+91 98200 11111",
            "email": "aarav.mehta@meridiantextiles.example",
            "address": "Surat, Gujarat",
            "notes": "Prefers email before 11 AM.",
            "category": self.world["categories"]["Client"].pk,
        }
        data.update(overrides)
        return data

    def test_create_contact_assigns_creator_and_redirects_to_profile(self):
        response = self.client.post(reverse("contacts:create"), self.payload())
        contact = Contact.objects.get(email="aarav.mehta@meridiantextiles.example")
        self.assertRedirects(
            response, reverse("contacts:detail", args=[contact.contact_id])
        )
        self.assertEqual(contact.created_by, self.world["admin"])
        self.assertEqual(contact.category.category_name, "Client")
        self.assertTrue(contact.reference.startswith("NX-"))

    def test_required_fields_are_validated(self):
        response = self.client.post(reverse("contacts:create"), {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), 0)
        self.assertContains(response, "This field is required.", count=5)

    def test_short_name_is_rejected(self):
        response = self.client.post(reverse("contacts:create"), self.payload(name="A"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at least 3 characters")
        self.assertEqual(Contact.objects.count(), 0)

    def test_duplicate_email_is_rejected(self):
        make_contact(self.world)
        existing = Contact.objects.first()
        response = self.client.post(
            reverse("contacts:create"),
            self.payload(
                name="Another Person",
                phone="+91 90000 22222",
                email=existing.email.upper(),
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already belongs to")
        self.assertEqual(Contact.objects.count(), 1)

    def test_duplicate_phone_with_different_formatting_is_rejected(self):
        existing = make_contact(self.world)  # +91 98200 30001
        response = self.client.post(
            reverse("contacts:create"),
            self.payload(
                name="Another Person",
                email="another@example.com",
                phone=existing.phone.replace(" ", ""),
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already saved for")
        self.assertEqual(Contact.objects.count(), 1)

    def test_invalid_phone_is_rejected(self):
        response = self.client.post(reverse("contacts:create"), self.payload(phone="abc"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "valid phone number")
        self.assertEqual(Contact.objects.count(), 0)

    def test_edit_contact_updates_record(self):
        contact = make_contact(self.world)
        response = self.client.post(
            reverse("contacts:edit", args=[contact.contact_id]),
            self.payload(
                name="Aarav R. Mehta",
                phone=contact.phone,
                email=contact.email,
                notes="Now prefers phone calls.",
            ),
        )
        self.assertRedirects(
            response, reverse("contacts:detail", args=[contact.contact_id])
        )
        contact.refresh_from_db()
        self.assertEqual(contact.name, "Aarav R. Mehta")
        self.assertEqual(contact.notes, "Now prefers phone calls.")

    def test_search_filters_and_sort(self):
        make_contact(self.world, name="Aarav Mehta", company="Meridian Textiles")
        make_contact(self.world, name="Isha Sharma", company="Northwind Logistics", category="Supplier")

        response = self.client.get(reverse("contacts:list"), {"q": "Northwind"})
        self.assertContains(response, "Isha Sharma")
        self.assertNotContains(response, "Aarav Mehta")

        response = self.client.get(
            reverse("contacts:list"), {"category": self.world["categories"]["Client"].pk}
        )
        self.assertContains(response, "Aarav Mehta")
        self.assertNotContains(response, "Isha Sharma")

        response = self.client.get(reverse("contacts:list"), {"sort": "name_asc"})
        self.assertEqual(response.status_code, 200)
        self.assertLess(
            response.content.decode().find("Aarav Mehta"),
            response.content.decode().find("Isha Sharma"),
        )

    def test_pagination_splits_large_directories(self):
        for index in range(12):
            make_contact(self.world, name=f"Contact Number {index}", company=f"Company {index}")
        response = self.client.get(reverse("contacts:list"))
        self.assertEqual(len(response.context["page_obj"].object_list), 10)
        response = self.client.get(reverse("contacts:list"), {"page": 2})
        self.assertEqual(len(response.context["page_obj"].object_list), 2)

    def test_profile_page_shows_history(self):
        contact = make_contact(self.world)
        make_interaction(self.world, contact, days_ago=2, interaction_type="meeting")
        make_followup(self.world, contact, due_days=4)
        response = self.client.get(reverse("contacts:detail", args=[contact.contact_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Discussed the quarterly order")
        self.assertContains(response, "Send the revised quotation")
        self.assertContains(response, "Prefers email before 11 AM.")

    def test_contact_directory_redesign_elements(self):
        contact = make_contact(self.world, name="Priya Nair", company="Acme Corp")
        make_interaction(self.world, contact, days_ago=5)
        response = self.client.get(reverse("contacts:list"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # Grid and card layout
        self.assertIn("nx-contact-grid", content)
        self.assertIn("nx-contact-card", content)
        self.assertIn("Priya Nair", content)
        self.assertIn("Acme Corp", content)

        # Avatar and activity indicator
        self.assertIn("nx-contact-card__avatar", content)
        self.assertIn("nx-contact-card__status", content)

        # Three circular action buttons
        self.assertIn(f'href="tel:{contact.phone}"', content)
        self.assertIn(f'href="mailto:{contact.email}"', content)
        self.assertIn(reverse("contacts:detail", args=[contact.contact_id]), content)

        # Three-dot menu actions
        self.assertIn(reverse("contacts:edit", args=[contact.contact_id]), content)
        self.assertIn(reverse("contacts:delete", args=[contact.contact_id]), content)
        self.assertIn("data-confirm-url", content)

        # Compact stats
        self.assertIn("Total Contacts", content)
        self.assertIn("Active Contacts", content)
        self.assertIn("Total Categories", content)

        # Header actions
        self.assertIn("Add New Contact", content)
        self.assertIn(reverse("contacts:create"), content)
        self.assertIn("Contacts", content)

    def test_field_scoped_search(self):
        c1 = make_contact(
            self.world,
            name="Rahul Varma",
            company="Varma Enterprises",
        )
        c2 = make_contact(
            self.world,
            name="Sneha Kapoor",
            company="Kapoor Logistics",
        )

        # Search by Name
        resp = self.client.get(reverse("contacts:list"), {"field": "name", "q": "Rahul"})
        self.assertContains(resp, "Rahul Varma")
        self.assertNotContains(resp, "Sneha Kapoor")

        # Search by Company
        resp = self.client.get(reverse("contacts:list"), {"field": "company", "q": "Kapoor"})
        self.assertContains(resp, "Sneha Kapoor")
        self.assertNotContains(resp, "Rahul Varma")

        # Search by Email
        resp = self.client.get(reverse("contacts:list"), {"field": "email", "q": c1.email})
        self.assertContains(resp, "Rahul Varma")
        self.assertNotContains(resp, "Sneha Kapoor")

        # Search by Phone (using part of the phone string)
        phone_part = c2.phone[-4:]
        resp = self.client.get(reverse("contacts:list"), {"field": "phone", "q": phone_part})
        self.assertContains(resp, "Sneha Kapoor")
        self.assertNotContains(resp, "Rahul Varma")


class CategoryTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.client.login(username="admin", password=PASSWORD)

    def test_create_category(self):
        response = self.client.post(
            reverse("contacts:category_create"),
            {"category_name": "Distributor", "description": "Regional distributors"},
        )
        self.assertRedirects(response, reverse("contacts:category_list"))
        self.assertTrue(Category.objects.filter(category_name="Distributor").exists())

    def test_duplicate_category_name_is_rejected(self):
        response = self.client.post(
            reverse("contacts:category_create"), {"category_name": "Client"}
        )
        self.assertRedirects(response, reverse("contacts:category_list"))
        self.assertEqual(Category.objects.filter(category_name__iexact="Client").count(), 1)

    def test_category_in_use_cannot_be_deleted(self):
        contact = make_contact(self.world)
        category = contact.category
        response = self.client.post(
            reverse("contacts:category_delete", args=[category.category_id]), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())
        self.assertContains(response, "still used by")

    def test_unused_category_can_be_deleted(self):
        category = Category.objects.create(category_name="Temporary")
        response = self.client.post(
            reverse("contacts:category_delete", args=[category.category_id])
        )
        self.assertRedirects(response, reverse("contacts:category_list"))
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())
