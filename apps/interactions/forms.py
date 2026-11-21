"""Form for recording an interaction."""

from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.forms import StyledFormMixin
from apps.contacts.models import Contact

from .models import Interaction


class InteractionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Interaction
        fields = ["contact", "interaction_type", "interaction_date", "notes"]
        widgets = {
            "interaction_date": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "What was discussed, agreed or promised?",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        contact = kwargs.pop("contact", None)
        super().__init__(*args, **kwargs)
        self.fields["contact"].queryset = Contact.objects.order_by("name")
        self.fields["contact"].empty_label = "Select a contact"
        if contact is not None:
            self.fields["contact"].initial = contact
        self.fields["interaction_date"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
        ]
        if not self.initial.get("interaction_date"):
            self.initial["interaction_date"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")

    def clean_notes(self):
        notes = (self.cleaned_data.get("notes") or "").strip()
        if len(notes) < 5:
            raise ValidationError("Add a short note so the history is useful later.")
        return notes

    def clean_interaction_date(self):
        when = self.cleaned_data["interaction_date"]
        if when > timezone.now() + timedelta(minutes=10):
            raise ValidationError("An interaction cannot be logged in the future.")
        return when
