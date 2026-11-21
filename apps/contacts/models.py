"""Category and Contact models."""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        ordering = ["category_name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.category_name

    @property
    def contact_count(self):
        return self.contacts.count()

    @property
    def slug(self):
        return self.category_name.lower().replace(" ", "-")


class Contact(models.Model):
    contact_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=160, db_index=True)
    company = models.CharField(max_length=160, blank=True, db_index=True)
    job_title = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, unique=True)
    email = models.EmailField(max_length=190, unique=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="contacts", db_column="category_id"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="contacts_created",
        db_column="created_by",
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contacts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"], name="idx_contacts_name"),
            models.Index(fields=["company"], name="idx_contacts_company"),
            models.Index(fields=["category", "created_at"], name="idx_contacts_category"),
            models.Index(fields=["created_at"], name="idx_contacts_created"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(name__gt=""), name="contacts_name_not_empty"
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def reference(self):
        return f"NX-{self.contact_id:04d}"

    @property
    def initials(self):
        parts = [part for part in self.name.split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def last_interaction(self):
        return self.interactions.order_by("-interaction_date").first()

    @property
    def open_followups(self):
        return self.followups.filter(status="pending")

    @property
    def is_active(self):
        cutoff = timezone.now() - timezone.timedelta(days=90)
        return self.interactions.filter(interaction_date__gte=cutoff).exists()

    def delete(self, *args, **kwargs):
        # Interactions and follow-ups cascade, contacts never orphan records.
        return super().delete(*args, **kwargs)
