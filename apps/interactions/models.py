"""Interaction records logged against a contact."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Interaction(models.Model):
    TYPE_CALL = "call"
    TYPE_MEETING = "meeting"
    TYPE_EMAIL = "email"
    TYPE_OTHER = "other"
    TYPE_CHOICES = (
        (TYPE_CALL, "Phone Call"),
        (TYPE_MEETING, "Meeting"),
        (TYPE_EMAIL, "Email"),
        (TYPE_OTHER, "Other"),
    )

    interaction_id = models.AutoField(primary_key=True)
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="interactions",
        db_column="contact_id",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="interactions",
        db_column="user_id",
    )
    interaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    notes = models.TextField()
    interaction_date = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "interactions"
        ordering = ["-interaction_date"]
        indexes = [
            models.Index(fields=["contact", "-interaction_date"], name="idx_inter_contact_date"),
            models.Index(fields=["interaction_type"], name="idx_inter_type"),
        ]

    def __str__(self):
        return f"{self.get_interaction_type_display()} with {self.contact.name}"

    @property
    def icon(self):
        return {
            self.TYPE_CALL: "phone",
            self.TYPE_MEETING: "meeting",
            self.TYPE_EMAIL: "mail",
            self.TYPE_OTHER: "note",
        }.get(self.interaction_type, "note")

    @property
    def tone(self):
        return {
            self.TYPE_CALL: "forest",
            self.TYPE_MEETING: "sage",
            self.TYPE_EMAIL: "amber",
            self.TYPE_OTHER: "muted",
        }.get(self.interaction_type, "muted")
