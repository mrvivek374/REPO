"""Contact and category forms, including duplicate detection."""

import re

from django import forms
from django.core.exceptions import ValidationError

from apps.accounts.forms import StyledFormMixin

from .models import Category, Contact

PHONE_RE = re.compile(r"^[0-9+\-()\s]{7,30}$")


def normalise_phone(value: str) -> str:
    """Reduce a phone number to digits for duplicate comparison."""
    return re.sub(r"\D", "", value or "")


class ContactForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "company", "job_title", "phone", "email", "address", "notes", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Aarav Mehta", "autofocus": True}),
            "company": forms.TextInput(attrs={"placeholder": "e.g. Meridian Textiles"}),
            "job_title": forms.TextInput(attrs={"placeholder": "e.g. Procurement Lead"}),
            "phone": forms.TextInput(attrs={"placeholder": "+91 98765 43210"}),
            "email": forms.EmailInput(attrs={"placeholder": "name@company.com"}),
            "address": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Street, city, state, postal code"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Context worth remembering about this contact"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "Select a category"
        self.fields["company"].required = True

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 3:
            raise ValidationError("Enter the contact's full name (at least 3 characters).")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not PHONE_RE.match(phone):
            raise ValidationError(
                "Enter a valid phone number using digits, spaces, +, - or brackets."
            )
        key = normalise_phone(phone)
        if len(key) < 7:
            raise ValidationError("A phone number needs at least 7 digits.")

        others = Contact.objects.all()
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        for existing in others.values_list("contact_id", "phone", "name"):
            if normalise_phone(existing[1]) == key:
                raise ValidationError(
                    f"This phone number is already saved for {existing[2]} "
                    f"(NX-{existing[0]:04d})."
                )
        return phone

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        others = Contact.objects.filter(email__iexact=email)
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        duplicate = others.first()
        if duplicate:
            raise ValidationError(
                f"This email address already belongs to {duplicate.name} "
                f"(NX-{duplicate.contact_id:04d})."
            )
        return email


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["category_name", "description"]
        widgets = {
            "category_name": forms.TextInput(attrs={"placeholder": "e.g. Distributor"}),
            "description": forms.TextInput(
                attrs={"placeholder": "How this group of contacts is used"}
            ),
        }

    def clean_category_name(self):
        name = (self.cleaned_data.get("category_name") or "").strip()
        others = Category.objects.filter(category_name__iexact=name)
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise ValidationError("A category with that name already exists.")
        return name
