"""Tests for interaction recording, validation and permissions."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.testing import PASSWORD, build_world, make_contact, make_interaction

from .models import Interaction


class InteractionTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.contact = make_contact(self.world)

    def test_staff_records_an_interaction(self):
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.post(
            reverse("interactions:create"),
            {
                "contact": self.contact.pk,
                "interaction_type": "meeting",
                "interaction_date": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "notes": "Reviewed the annual contract and agreed next steps.",
            },
        )
        self.assertRedirects(
            response, reverse("contacts:detail", args=[self.contact.contact_id])
        )
        interaction = Interaction.objects.get()
        self.assertEqual(interaction.user, self.world["staff"])
        self.assertEqual(interaction.interaction_type, "meeting")

    def test_notes_are_required(self):
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.post(
            reverse("interactions:create"),
            {
                "contact": self.contact.pk,
                "interaction_type": "call",
                "interaction_date": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "notes": "hi",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "short note")
        self.assertEqual(Interaction.objects.count(), 0)

    def test_future_interaction_is_rejected(self):
        self.client.login(username="staff", password=PASSWORD)
        future = timezone.localtime() + timedelta(days=2)
        response = self.client.post(
            reverse("interactions:create"),
            {
                "contact": self.contact.pk,
                "interaction_type": "call",
                "interaction_date": future.strftime("%Y-%m-%dT%H:%M"),
                "notes": "A note that should not be saved in the future.",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be logged in the future")
        self.assertEqual(Interaction.objects.count(), 0)

    def test_timeline_lists_and_filters(self):
        make_interaction(self.world, self.contact, interaction_type="email")
        self.client.login(username="manager", password=PASSWORD)
        response = self.client.get(reverse("interactions:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email")
        response = self.client.get(reverse("interactions:list"), {"type": "call"})
        self.assertNotContains(response, "Discussed the quarterly order")

    def test_author_can_delete_own_interaction(self):
        interaction = make_interaction(self.world, self.contact)
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.post(
            reverse("interactions:delete", args=[interaction.interaction_id])
        )
        self.assertRedirects(
            response, reverse("contacts:detail", args=[self.contact.contact_id])
        )
        self.assertFalse(Interaction.objects.filter(pk=interaction.pk).exists())

    def test_other_staff_cannot_delete_foreign_interaction(self):
        interaction = make_interaction(self.world, self.contact)
        self.client.login(username="arjun", password=PASSWORD)
        response = self.client.post(
            reverse("interactions:delete", args=[interaction.interaction_id])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Interaction.objects.filter(pk=interaction.pk).exists())
