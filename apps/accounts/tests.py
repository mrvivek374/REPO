"""Tests for authentication, user management and role permissions."""

from django.test import TestCase
from django.urls import reverse

from .models import Role, User
from .testing import PASSWORD, build_world


class AuthenticationTests(TestCase):
    def setUp(self):
        self.world = build_world()

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "admin", "password": PASSWORD}
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.world["admin"].pk)

    def test_login_with_email_address(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "rohan@nexora.example", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_login_with_invalid_credentials(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "admin", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Incorrect username or password")

    def test_inactive_account_cannot_sign_in(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "kavya", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "deactivated")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post_and_clears_session(self):
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_root_redirects_by_auth_state(self):
        self.assertRedirects(self.client.get("/"), reverse("accounts:login"))
        self.client.login(username="staff", password=PASSWORD)
        self.assertRedirects(self.client.get("/"), reverse("dashboard"))


class RolePermissionTests(TestCase):
    def setUp(self):
        self.world = build_world()

    def test_staff_cannot_open_user_management(self):
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_view_reports_but_not_team(self):
        self.client.login(username="manager", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("reports:reports")).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)

    def test_staff_cannot_view_reports(self):
        self.client.login(username="staff", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("reports:reports")).status_code, 403)

    def test_staff_cannot_manage_categories(self):
        self.client.login(username="staff", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("contacts:category_list")).status_code, 200)
        response = self.client.post(
            reverse("contacts:category_create"), {"category_name": "Vendor"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            self.world["categories"]["Client"].__class__.objects.filter(
                category_name="Vendor"
            ).exists()
        )

    def test_staff_cannot_delete_contacts(self):
        from .testing import make_contact

        contact = make_contact(self.world)
        self.client.login(username="staff", password=PASSWORD)
        response = self.client.post(reverse("contacts:delete", args=[contact.contact_id]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(type(contact).objects.filter(pk=contact.pk).exists())

    def test_admin_can_delete_contacts(self):
        from .testing import make_contact

        contact = make_contact(self.world)
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.post(reverse("contacts:delete", args=[contact.contact_id]))
        self.assertRedirects(response, reverse("contacts:list"))
        self.assertFalse(type(contact).objects.filter(pk=contact.pk).exists())


class UserManagementTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.client.login(username="admin", password=PASSWORD)

    def test_admin_creates_a_team_member(self):
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "name": "Neha Kulkarni",
                "username": "neha",
                "email": "neha@nexora.example",
                "job_title": "Account Manager",
                "phone": "+91 90000 11111",
                "role": self.world["roles"]["staff"].pk,
                "status": User.STATUS_ACTIVE,
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertRedirects(response, reverse("accounts:user_list"))
        created = User.objects.get(username="neha")
        self.assertTrue(created.check_password("StrongPass123"))

    def test_duplicate_username_is_rejected(self):
        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "name": "Duplicate",
                "username": "staff",
                "email": "dupe@nexora.example",
                "role": self.world["roles"]["staff"].pk,
                "status": User.STATUS_ACTIVE,
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already taken")

    def test_admin_can_deactivate_a_staff_account(self):
        response = self.client.post(
            reverse("accounts:user_toggle_status", args=[self.world["staff"].pk])
        )
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.world["staff"].refresh_from_db()
        self.assertEqual(self.world["staff"].status, User.STATUS_INACTIVE)

    def test_admin_cannot_deactivate_own_account(self):
        response = self.client.post(
            reverse("accounts:user_toggle_status", args=[self.world["admin"].pk])
        )
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.world["admin"].refresh_from_db()
        self.assertEqual(self.world["admin"].status, User.STATUS_ACTIVE)

    def test_last_administrator_can_be_neither_deleted_nor_demoted(self):
        response = self.client.post(
            reverse("accounts:user_delete", args=[self.world["admin"].pk])
        )
        self.assertRedirects(response, reverse("accounts:user_list"))
        self.assertTrue(User.objects.filter(pk=self.world["admin"].pk).exists())

    def test_role_permissions_can_be_updated(self):
        staff_role = self.world["roles"]["staff"]
        response = self.client.post(
            reverse("accounts:role_edit", args=[staff_role.pk]),
            {"reports.view": "on"},
        )
        self.assertRedirects(response, reverse("accounts:role_list"))
        staff_role.refresh_from_db()
        self.assertIn("reports.view", staff_role.permissions)
        self.assertNotIn("users.manage", staff_role.permissions)

    def test_administrator_role_is_locked(self):
        admin_role = self.world["roles"]["admin"]
        response = self.client.post(
            reverse("accounts:role_edit", args=[admin_role.pk]), {"reports.view": "on"}
        )
        self.assertRedirects(response, reverse("accounts:role_list"))
        admin_role.refresh_from_db()
        self.assertIn("users.manage", admin_role.permissions)

    def test_role_list_and_matrix_render(self):
        response = self.client.get(reverse("accounts:role_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Permission matrix")
        self.assertContains(response, "Manage users, roles and permissions")


class ProfileAndSettingsTests(TestCase):
    def setUp(self):
        self.world = build_world()
        self.client.login(username="staff", password=PASSWORD)

    def test_profile_update(self):
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "name": "Priya Nair",
                "email": "priya.nair@nexora.example",
                "job_title": "Senior Executive",
                "phone": "+91 98765 00000",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.world["staff"].refresh_from_db()
        self.assertEqual(self.world["staff"].job_title, "Senior Executive")

    def test_preferences_are_saved(self):
        response = self.client.post(
            reverse("accounts:settings"),
            {"items_per_page": 15, "date_format": "d/m/Y", "compact_tables": "on"},
        )
        self.assertRedirects(response, reverse("accounts:settings"))
        prefs = self.world["staff"].preferences()
        prefs.refresh_from_db()
        self.assertEqual(prefs.items_per_page, 15)
        self.assertTrue(prefs.compact_tables)

    def test_password_change_works(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "BetterPass456",
                "new_password2": "BetterPass456",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.world["staff"].refresh_from_db()
        self.assertTrue(self.world["staff"].check_password("BetterPass456"))
