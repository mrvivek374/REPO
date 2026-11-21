"""Form for creating and editing follow-up tasks."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.forms import StyledFormMixin
from apps.contacts.models import Contact

from .models import FollowUp

User = get_user_model()


class FollowUpForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ["contact", "assigned_to", "due_date", "notes"]
        widgets = {
            "due_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3, "placeholder": "What needs to happen in this follow-up?"}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.acting_user = kwargs.pop("acting_user", None)
        self.restrict_assignee = kwargs.pop("restrict_assignee", False)
        contact = kwargs.pop("contact", None)
        super().__init__(*args, **kwargs)

        self.fields["contact"].queryset = Contact.objects.order_by("name")
        self.fields["contact"].empty_label = "Select a contact"
        if contact is not None:
            self.fields["contact"].initial = contact

        assignees = User.objects.filter(status=User.STATUS_ACTIVE).select_related("role")
        if self.restrict_assignee and self.acting_user is not None:
            assignees = assignees.filter(pk=self.acting_user.pk)
        self.fields["assigned_to"].queryset = assignees.order_by("name")
        self.fields["assigned_to"].empty_label = "Assign to a team member"
        if self.acting_user is not None and not self.instance.pk:
            self.fields["assigned_to"].initial = self.acting_user

        self.fields["due_date"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]
        if not self.instance.pk and not self.initial.get("due_date"):
            tomorrow = timezone.localtime() + timezone.timedelta(days=1)
            self.initial["due_date"] = tomorrow.strftime("%Y-%m-%dT%H:%M")

    def clean_due_date(self):
        due = self.cleaned_data["due_date"]
        if not self.instance.pk and due < timezone.now():
            raise ValidationError("Choose a due date and time in the future.")
        if self.instance.pk:
            previous = FollowUp.objects.get(pk=self.instance.pk).due_date
            if previous != due and due < timezone.now():
                raise ValidationError(
                    "The new due date is already in the past. Pick a later date."
                )
        return due

    def clean_notes(self):
        notes = (self.cleaned_data.get("notes") or "").strip()
        if len(notes) < 5:
            raise ValidationError("Describe the follow-up in a few words.")
        return notes
