"""Seed NEXORA with the initial demonstration dataset.

    python manage.py seed_demo           # safe, adds only what is missing
    python manage.py seed_demo --reset   # clears contacts/history first

Every record below is fictional.
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.contacts.models import Category, Contact
from apps.followups.models import FollowUp
from apps.interactions.models import Interaction

DEMO_PASSWORD = "Nexora@123"

CATEGORIES = [
    ("Client", "Paying customers with active business relationships."),
    ("Supplier", "Vendors and manufacturers who supply goods or services."),
    ("Partner", "Channel, distribution and reseller partners."),
    ("Lead", "Qualified prospects still in the pipeline."),
]

USERS = [
    {
        "name": "Ananya Kapoor",
        "username": "admin",
        "email": "ananya.kapoor@nexora.example",
        "role": "admin",
        "job_title": "System Administrator",
        "phone": "+91 98200 11001",
        "status": User.STATUS_ACTIVE,
    },
    {
        "name": "Rohan Desai",
        "username": "manager",
        "email": "rohan.desai@nexora.example",
        "role": "manager",
        "job_title": "Business Development Manager",
        "phone": "+91 98200 11002",
        "status": User.STATUS_ACTIVE,
    },
    {
        "name": "Priya Nair",
        "username": "staff",
        "email": "priya.nair@nexora.example",
        "role": "staff",
        "job_title": "Relationship Executive",
        "phone": "+91 98200 11003",
        "status": User.STATUS_ACTIVE,
    },
    {
        "name": "Arjun Menon",
        "username": "arjun",
        "email": "arjun.menon@nexora.example",
        "role": "staff",
        "job_title": "Account Coordinator",
        "phone": "+91 98200 11004",
        "status": User.STATUS_ACTIVE,
    },
    {
        "name": "Kavya Rao",
        "username": "kavya",
        "email": "kavya.rao@nexora.example",
        "role": "staff",
        "job_title": "Inside Sales Associate",
        "phone": "+91 98200 11005",
        "status": User.STATUS_INACTIVE,
    },
]

CONTACTS = [
    ("Aarav Mehta", "Meridian Textiles", "Procurement Lead", "Client", "Surat, Gujarat"),
    ("Isha Sharma", "Northwind Logistics", "Head of Operations", "Client", "Pune, Maharashtra"),
    ("Kabir Rao", "Verdant Foods", "Founder", "Lead", "Bengaluru, Karnataka"),
    ("Meera Iyer", "Bluepeak Analytics", "Director", "Partner", "Chennai, Tamil Nadu"),
    ("Rohan Kapoor", "Sable Packaging", "Purchase Manager", "Supplier", "Noida, Uttar Pradesh"),
    ("Ananya Deshmukh", "Lumen Interiors", "Principal Designer", "Client", "Mumbai, Maharashtra"),
    ("Vikram Nair", "Coastline Exports", "Export Manager", "Partner", "Kochi, Kerala"),
    ("Sneha Gupta", "Harmony Clinics", "Administrator", "Lead", "Jaipur, Rajasthan"),
    ("Arjun Malhotra", "Trailhead Outdoors", "Category Buyer", "Client", "Dehradun, Uttarakhand"),
    ("Divya Menon", "Greenline Farms", "Co-founder", "Supplier", "Coimbatore, Tamil Nadu"),
    ("Nikhil Bansal", "Ironwood Furniture", "Production Head", "Supplier", "Jodhpur, Rajasthan"),
    ("Tara Joshi", "Lattice Studio", "Creative Director", "Lead", "Ahmedabad, Gujarat"),
    ("Sameer Khan", "Nova Freight", "Key Account Manager", "Partner", "Hyderabad, Telangana"),
    ("Priyanka Shetty", "Brightpath Academy", "Admissions Head", "Client", "Mangaluru, Karnataka"),
    ("Yash Patel", "Kinetic Motors", "Workshop Owner", "Supplier", "Vadodara, Gujarat"),
    ("Riya Sen", "Paperleaf Press", "Managing Partner", "Partner", "Kolkata, West Bengal"),
    ("Aditya Verma", "Summit Realty", "Sales Director", "Lead", "Gurugram, Haryana"),
    ("Neha Kulkarni", "Cobalt Systems", "IT Manager", "Client", "Pune, Maharashtra"),
    ("Karan Bhatia", "Farmstead Dairy", "Distribution Lead", "Supplier", "Ludhiana, Punjab"),
    ("Pooja Agarwal", "Auraluxe Jewels", "Owner", "Client", "Mumbai, Maharashtra"),
    ("Manish Tiwari", "Urban Grid Energy", "Project Lead", "Partner", "Bhopal, Madhya Pradesh"),
    ("Lakshmi Reddy", "Sailfish Seafoods", "Export Head", "Client", "Visakhapatnam, Andhra Pradesh"),
    ("Farhan Ali", "Ridgeway Hotels", "F&B Manager", "Lead", "Lucknow, Uttar Pradesh"),
    ("Shreya Bose", "Fern & Fig", "Founder", "Lead", "Kolkata, West Bengal"),
    ("Gaurav Sethi", "Quantis Legal", "Partner", "Partner", "New Delhi, Delhi"),
]

PHONE_PREFIXES = ["98200", "98330", "96110", "90040", "87670", "99870", "70210", "81450"]

INTERACTION_NOTES = {
    "call": [
        "Called to confirm the quarterly order volume and delivery window.",
        "Discussed pricing revision; they asked for a proposal by Friday.",
        "Quick check-in on the pending invoice and payment timeline.",
        "They confirmed the renewal conversation for next month.",
    ],
    "meeting": [
        "In-person review of the account plan and upcoming requirements.",
        "Met at their office to walk through the new catalogue.",
        "Introductory meeting; mapped decision makers and next steps.",
        "Quarterly business review — satisfaction high, upsell opportunity noted.",
    ],
    "email": [
        "Sent the updated rate card and availability sheet.",
        "Shared the onboarding checklist and asked for documentation.",
        "Followed up on the proposal with a short summary.",
        "Received a purchase enquiry; forwarded to the operations desk.",
    ],
    "other": [
        "Shared product samples through courier; awaiting feedback.",
        "Added them to the partner newsletter list.",
        "Updated the record after a referral from an existing client.",
    ],
}

FOLLOWUP_NOTES = [
    "Send the revised quotation and confirm delivery dates.",
    "Call back about the annual contract renewal.",
    "Collect GST details before raising the invoice.",
    "Schedule a product demo with their operations team.",
    "Confirm payment status with the accounts department.",
    "Share the onboarding guide and training dates.",
    "Check whether the trial batch met expectations.",
    "Reconnect after their internal review meeting.",
]


class Command(BaseCommand):
    help = "Create roles, categories, demo users, contacts, interactions and follow-ups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all contacts, interactions and follow-ups before seeding.",
        )

    def handle(self, *args, **options):
        random.seed(20261118)
        now = timezone.now()

        if options["reset"]:
            FollowUp.objects.all().delete()
            Interaction.objects.all().delete()
            Contact.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing demo records."))

        # Roles -----------------------------------------------------------------
        for preset in Role.defaults():
            role, created = Role.objects.get_or_create(
                role_key=preset["role_key"],
                defaults={
                    "role_name": preset["role_name"],
                    "description": preset["description"],
                    "permissions": preset["permissions"],
                },
            )
            if not created and not role.permissions:
                role.permissions = preset["permissions"]
                role.save(update_fields=["permissions"])
        self.stdout.write(f"Roles ready: {', '.join(Role.objects.values_list('role_name', flat=True))}")

        # Categories ------------------------------------------------------------
        for name, description in CATEGORIES:
            Category.objects.get_or_create(
                category_name=name, defaults={"description": description}
            )

        # Users -----------------------------------------------------------------
        for spec in USERS:
            role = Role.objects.get(role_key=spec["role"])
            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "name": spec["name"],
                    "email": spec["email"],
                    "role": role,
                    "job_title": spec["job_title"],
                    "phone": spec["phone"],
                    "status": spec["status"],
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                user.preferences()
            else:
                user.role = role
                user.name = spec["name"]
                user.email = spec["email"]
                user.job_title = spec["job_title"]
                user.status = spec["status"]
                user.save()

        if Contact.objects.exists():
            self.stdout.write(
                self.style.SUCCESS(
                    "Demo data already present. Use --reset to rebuild contacts and history."
                )
            )
            self._print_accounts()
            return

        staff = list(User.objects.filter(role__role_key__in=["admin", "staff"]))
        admins_and_managers = list(User.objects.filter(role__role_key__in=["admin", "manager"]))

        # Contacts --------------------------------------------------------------
        contacts = []
        for index, (name, company, title, category_name, address) in enumerate(CONTACTS):
            category = Category.objects.get(category_name=category_name)
            slug = company.lower().replace(" & ", "").replace(" ", "")
            phone = f"+91 {random.choice(PHONE_PREFIXES)} {random.randint(10000, 99999)}"
            while Contact.objects.filter(phone=phone).exists():
                phone = f"+91 {random.choice(PHONE_PREFIXES)} {random.randint(10000, 99999)}"
            first, last = name.split(" ", 1)
            email = f"{first.lower()}.{last.lower().replace(' ', '')}@{slug}.example"
            created_at = now - timedelta(days=random.randint(0, 168), hours=random.randint(0, 20))
            contact = Contact.objects.create(
                name=name,
                company=company,
                job_title=title,
                phone=phone,
                email=email,
                address=address,
                notes="Introduced through the regional business network. "
                      "Prefers communication over email before 11 AM.",
                category=category,
                created_by=random.choice(admins_and_managers),
                created_at=created_at,
            )
            contacts.append(contact)

        # Interactions ----------------------------------------------------------
        interaction_total = 0
        for contact in contacts:
            for _ in range(random.randint(0, 4)):
                days_ago = random.randint(0, max((now - contact.created_at).days, 1))
                when = now - timedelta(days=days_ago, hours=random.randint(0, 8))
                if when < contact.created_at:
                    when = contact.created_at + timedelta(hours=2)
                interaction_type = random.choice([choice[0] for choice in Interaction.TYPE_CHOICES])
                Interaction.objects.create(
                    contact=contact,
                    user=random.choice(staff),
                    interaction_type=interaction_type,
                    notes=random.choice(INTERACTION_NOTES[interaction_type]),
                    interaction_date=when,
                )
                interaction_total += 1

        # Follow-ups ------------------------------------------------------------
        followup_total = 0
        for index, contact in enumerate(contacts):
            bucket = index % 3
            if bucket == 0:  # upcoming
                due = now + timedelta(days=random.randint(1, 9), hours=random.randint(1, 6))
                followup = FollowUp.objects.create(
                    contact=contact,
                    assigned_to=random.choice(staff),
                    due_date=due,
                    status=FollowUp.STATUS_PENDING,
                    notes=random.choice(FOLLOWUP_NOTES),
                    created_by=random.choice(admins_and_managers),
                )
            elif bucket == 1:  # overdue
                due = now - timedelta(days=random.randint(1, 10), hours=random.randint(0, 5))
                followup = FollowUp.objects.create(
                    contact=contact,
                    assigned_to=random.choice(staff),
                    due_date=due,
                    status=FollowUp.STATUS_PENDING,
                    notes=random.choice(FOLLOWUP_NOTES),
                    created_by=random.choice(admins_and_managers),
                )
            else:  # completed
                completed_at = now - timedelta(days=random.randint(1, 30))
                due = completed_at - timedelta(days=random.randint(0, 3))
                followup = FollowUp.objects.create(
                    contact=contact,
                    assigned_to=random.choice(staff),
                    due_date=due,
                    status=FollowUp.STATUS_COMPLETED,
                    notes=random.choice(FOLLOWUP_NOTES),
                    created_by=random.choice(admins_and_managers),
                    completed_at=completed_at,
                )
            followup_total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {Contact.objects.count()} contacts, {interaction_total} interactions "
                f"and {followup_total} follow-ups."
            )
        )
        self._print_accounts()

    def _print_accounts(self):
        self.stdout.write("")
        self.stdout.write("Demo accounts (password %s):" % DEMO_PASSWORD)
        for user in User.objects.select_related("role").order_by("user_id"):
            state = "active" if user.status == User.STATUS_ACTIVE else "inactive"
            self.stdout.write(
                f"  {user.username:<10} {user.role.role_name:<28} {state}"
            )
