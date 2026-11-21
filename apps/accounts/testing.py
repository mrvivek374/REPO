"""Shared fixtures for the NEXORA test suite (not a test module)."""

from datetime import timedelta

from django.utils import timezone

from apps.contacts.models import Category, Contact
from apps.followups.models import FollowUp
from apps.interactions.models import Interaction

from .models import Role, User

PASSWORD = "Nexora@123"


def build_world():
    """Create the three roles, four categories and one user per role."""
    roles = {}
    for preset in Role.defaults():
        roles[preset["role_key"]] = Role.objects.create(
            role_name=preset["role_name"],
            role_key=preset["role_key"],
            description=preset["description"],
            permissions=preset["permissions"],
        )

    categories = {}
    for name, description in (
        ("Client", "Paying customers"),
        ("Supplier", "Vendors and suppliers"),
        ("Partner", "Channel partners"),
        ("Lead", "Qualified prospects"),
    ):
        categories[name] = Category.objects.create(
            category_name=name, description=description
        )

    admin = User.objects.create_user(
        "admin",
        PASSWORD,
        name="Ananya Kapoor",
        email="ananya@nexora.example",
        role=roles["admin"],
        status=User.STATUS_ACTIVE,
    )
    manager = User.objects.create_user(
        "manager",
        PASSWORD,
        name="Rohan Desai",
        email="rohan@nexora.example",
        role=roles["manager"],
        status=User.STATUS_ACTIVE,
    )
    staff = User.objects.create_user(
        "staff",
        PASSWORD,
        name="Priya Nair",
        email="priya@nexora.example",
        role=roles["staff"],
        status=User.STATUS_ACTIVE,
    )
    other_staff = User.objects.create_user(
        "arjun",
        PASSWORD,
        name="Arjun Menon",
        email="arjun@nexora.example",
        role=roles["staff"],
        status=User.STATUS_ACTIVE,
    )
    inactive = User.objects.create_user(
        "kavya",
        PASSWORD,
        name="Kavya Rao",
        email="kavya@nexora.example",
        role=roles["staff"],
        status=User.STATUS_INACTIVE,
    )

    return {
        "roles": roles,
        "categories": categories,
        "admin": admin,
        "manager": manager,
        "staff": staff,
        "other_staff": other_staff,
        "inactive": inactive,
    }


def make_contact(world, name="Aarav Mehta", company="Meridian Textiles", category="Client"):
    phone_seed = Contact.objects.count() + 1
    return Contact.objects.create(
        name=name,
        company=company,
        job_title="Procurement Lead",
        phone=f"+91 98200 3{phone_seed:04d}",
        email=f"contact{phone_seed}@example.com",
        address="Surat, Gujarat",
        category=world["categories"][category],
        created_by=world["admin"],
        notes="Prefers email before 11 AM.",
    )


def make_interaction(world, contact, days_ago=1, interaction_type="call"):
    return Interaction.objects.create(
        contact=contact,
        user=world["staff"],
        interaction_type=interaction_type,
        notes="Discussed the quarterly order and next steps.",
        interaction_date=timezone.now() - timedelta(days=days_ago),
    )


def make_followup(world, contact, due_days=3, assignee="staff", status="pending"):
    creator = world["admin"] if assignee != "staff" else world["staff"]
    task = FollowUp.objects.create(
        contact=contact,
        assigned_to=world[assignee],
        due_date=timezone.now() + timedelta(days=due_days),
        status=status,
        notes="Send the revised quotation and confirm dates.",
        created_by=creator,
    )
    if status == FollowUp.STATUS_COMPLETED:
        task.completed_at = timezone.now() - timedelta(days=1)
        task.save(update_fields=["completed_at"])
    return task
