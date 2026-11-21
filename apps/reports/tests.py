"""Tests proving dashboard and report figures come from the database."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.testing import (
    PASSWORD,
    build_world,
    make_contact,
    make_followup,
    make_interaction,
)


class DashboardTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.client.login(username="manager", password=PASSWORD)

    def test_dashboard_renders_live_statistics(self):
        first = make_contact(self.world, name="Aarav Mehta")
        second = make_contact(self.world, name="Isha Sharma", company="Northwind")
        make_interaction(self.world, first, interaction_type="call")
        make_followup(self.world, first, due_days=2)
        make_followup(self.world, second, due_days=-2)
        make_followup(self.world, second, due_days=-6, status="completed")

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

        stats = response.context["stats"]
        self.assertEqual(stats["total_contacts"], 2)
        self.assertEqual(stats["active_contacts"], 1)
        self.assertEqual(stats["total_categories"], 4)
        self.assertEqual(stats["upcoming_followups"], 1)
        self.assertEqual(stats["overdue_followups"], 1)
        self.assertEqual(stats["pending_followups"], 2)
        self.assertEqual(stats["completion_rate"], 33)
        self.assertEqual(len(response.context["activities"]), 2)

    def test_dashboard_chart_series_match_records(self):
        make_contact(self.world, name="Aarav Mehta")
        response = self.client.get(reverse("dashboard"))
        growth = response.context["growth_chart"]
        self.assertEqual(sum(growth["values"]), 1)
        distribution = response.context["category_chart"]
        self.assertEqual(sum(distribution["values"]), 1)

    def test_dashboard_shows_empty_states(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No contacts yet")
        self.assertContains(response, "No activity recorded")


class ReportPageTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.client.login(username="manager", password=PASSWORD)

        self.old_contact = make_contact(self.world, name="Old Contact")
        self.old_contact.created_at = timezone.now() - timedelta(days=40)
        self.old_contact.save(update_fields=["created_at"])

        self.new_contact = make_contact(self.world, name="New Contact", category="Lead")
        make_interaction(self.world, self.new_contact, days_ago=1, interaction_type="email")
        make_followup(self.world, self.new_contact, due_days=-1)

    def test_reports_page_renders(self):
        response = self.client.get(reverse("reports:reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reporting period")
        self.assertContains(response, "Contact report by category")

    def test_date_range_filters_totals(self):
        today = timezone.localdate()
        response = self.client.get(
            reverse("reports:reports"),
            {
                "start": (today - timedelta(days=7)).isoformat(),
                "end": today.isoformat(),
            },
        )
        self.assertEqual(response.context["new_contacts"], 1)
        self.assertEqual(response.context["interactions"], 1)
        self.assertEqual(response.context["followups"]["overdue"], 1)

        response = self.client.get(
            reverse("reports:reports"),
            {
                "start": (today - timedelta(days=90)).isoformat(),
                "end": today.isoformat(),
            },
        )
        self.assertEqual(response.context["new_contacts"], 2)

    def test_invalid_dates_fall_back_to_defaults(self):
        response = self.client.get(
            reverse("reports:reports"), {"start": "not-a-date", "end": "nope"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["end"], timezone.localdate())

    def test_category_table_shares_are_consistent(self):
        response = self.client.get(reverse("reports:reports"))
        rows = response.context["category_table"]
        self.assertEqual(sum(row["total"] for row in rows), 2)
        self.assertEqual(sum(row["share"] for row in rows), 100)
