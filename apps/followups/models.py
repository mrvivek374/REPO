"""Follow-up tasks assigned to team members."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class FollowUp(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
    )

    followup_id = models.AutoField(primary_key=True)
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="followups",
        db_column="contact_id",
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="followups_assigned",
        db_column="assigned_to",
        db_index=True,
    )
    due_date = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="followups_created",
        db_column="created_by",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "followups"
        ordering = ["due_date"]
        indexes = [
            models.Index(fields=["status", "due_date"], name="idx_follow_status_due"),
            models.Index(fields=["assigned_to", "status"], name="idx_follow_assignee"),
        ]

    def __str__(self):
        return f"Follow up with {self.contact.name} on {self.due_date:%d %b %Y}"

    @property
    def is_overdue(self):
        return self.status == self.STATUS_PENDING and self.due_date < timezone.now()

    @property
    def is_due_today(self):
        today = timezone.localdate()
        return self.status == self.STATUS_PENDING and timezone.localtime(self.due_date).date() == today

    @property
    def display_status(self):
        if self.status == self.STATUS_COMPLETED:
            return "completed"
        return "overdue" if self.is_overdue else "pending"

    @property
    def due_label(self):
        if self.status == self.STATUS_COMPLETED:
            return "Completed"
        days = (timezone.localtime(self.due_date).date() - timezone.localdate()).days
        if days == 0:
            return "Due today"
        if days == 1:
            return "Tomorrow"
        if days == -1:
            return "1 day overdue"
        if days < 0:
            return f"{-days} days overdue"
        return f"In {days} days"

    @property
    def display_status_label(self):
        return {
            "completed": "Completed",
            "overdue": "Overdue",
            "pending": "Pending",
        }[self.display_status]

    def mark_completed(self, when=None):
        self.status = self.STATUS_COMPLETED
        self.completed_at = when or timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def reopen(self):
        self.status = self.STATUS_PENDING
        self.completed_at = None
        self.save(update_fields=["status", "completed_at", "updated_at"])
