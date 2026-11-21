"""Tests for follow-up scheduling, status derivation and access rules."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.testing import PASSWORD, build_world, make_contact, make_followup

from .models import FollowUp


class FollowUpTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.contact = make_contact(self.world)

    def future_payload(self, **overrides):
        data = {
            "contact": self.contact.pk,
            "assigned_to": self.world["staff"].pk,
            "due_date": (timezone.localtime() + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M"),
            "notes": "Send the revised quotation and confirm delivery dates.",
        }
        data.update(overrides)
        return data

    def test_create_followup(self):
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.post(reverse("followups:create"), self.future_payload())
        self.assertRedirects(response, reverse("followups:list"))
        task = FollowUp.objects.get()
        self.assertEqual(task.status, FollowUp.STATUS_PENDING)
        self.assertEqual(task.created_by, self.world["admin"])
        self.assertFalse(task.is_overdue)

    def test_due_date_in_the_past_is_rejected(self):
        self.client.login(username="admin", password=PASSWORD)
        past = (timezone.localtime() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(
            reverse("followups:create"), self.future_payload(due_date=past)
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "due date and time in the future")
        self.assertEqual(FollowUp.objects.count(), 0)

    def test_notes_are_required(self):
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.post(
            reverse("followups:create"), self.future_payload(notes="x")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Describe the follow-up")
        self.assertEqual(FollowUp.objects.count(), 0)

    def test_overdue_status_is_derived_from_date(self):
        overdue = make_followup(self.world, self.contact, due_days=-3)
        upcoming = make_followup(self.world, self.contact, due_days=3)
        completed = make_followup(self.world, self.contact, due_days=-5, status="completed")

        self.assertEqual(overdue.display_status, "overdue")
        self.assertEqual(overdue.due_label, "3 days overdue")
        self.assertEqual(upcoming.display_status, "pending")
        self.assertEqual(completed.display_status, "completed")
        self.assertFalse(completed.is_overdue)

    def test_complete_and_reopen_task(self):
        task = make_followup(self.world, self.contact, due_days=2)
        self.client.login(username="staff", password=PASSWORD)

        response = self.client.post(reverse("followups:complete", args=[task.followup_id]))
        self.assertRedirects(response, reverse("followups:list"))
        task.refresh_from_db()
        self.assertEqual(task.status, FollowUp.STATUS_COMPLETED)
        self.assertIsNotNone(task.completed_at)

        response = self.client.post(reverse("followups:reopen", args=[task.followup_id]))
        task.refresh_from_db()
        self.assertEqual(task.status, FollowUp.STATUS_PENDING)
        self.assertIsNone(task.completed_at)

    def test_staff_cannot_edit_a_colleagues_task(self):
        task = make_followup(self.world, self.contact, assignee="other_staff")
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.get(reverse("followups:edit", args=[task.followup_id]))
        self.assertEqual(response.status_code, 403)

    def test_staff_only_sees_their_own_and_created_tasks(self):
        mine = make_followup(self.world, self.contact, assignee="staff")
        colleagues = make_followup(self.world, self.contact, assignee="other_staff")
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.get(reverse("followups:list"), {"tab": "all"})
        self.assertEqual(response.status_code, 200)
        page = response.context["page_obj"].object_list
        self.assertIn(mine, page)
        self.assertNotIn(colleagues, page)

    def test_staff_cannot_assign_to_another_user(self):
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.post(
            reverse("followups:create"),
            self.future_payload(assigned_to=self.world["other_staff"].pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FollowUp.objects.exists())

    def test_overdue_tab_only_lists_overdue_tasks(self):
        overdue = make_followup(self.world, self.contact, due_days=-2)
        upcoming = make_followup(self.world, self.contact, due_days=2)
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.get(reverse("followups:list"), {"tab": "overdue"})
        objects = response.context["page_obj"].object_list
        self.assertIn(overdue, objects)
        self.assertNotIn(upcoming, objects)
        self.assertEqual(response.context["counts"]["overdue"], 1)
