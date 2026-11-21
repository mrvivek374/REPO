"""Forms for authentication, user management, profile and settings."""

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError

from .models import Role, UserPreference

User = get_user_model()


class StyledFormMixin:
    """Apply NEXORA's neumorphic field classes without repeating widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = f"{css} nx-switch".strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = f"{css} nx-select".strip()
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = f"{css} nx-file".strip()
            else:
                widget.attrs["class"] = f"{css} nx-input".strip()
            if field.required and not isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("aria-required", "true")


class LoginForm(StyledFormMixin, forms.Form):
    username = forms.CharField(
        label="Username",
        max_length=190,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter your username",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter your password", "autocomplete": "current-password"}
        ),
    )
    remember = forms.BooleanField(label="Remember me", required=False, initial=False)

    error_messages = {
        "invalid": "Incorrect username or password. Please try again.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)
        self.fields["remember"].widget.attrs["class"] = "nx-check"

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        password = cleaned.get("password")
        if username and password:
            self.user_cache = authenticate(
                self.request, username=username.strip(), password=password
            )
            if self.user_cache is None:
                if User.objects.filter(username__iexact=username.strip()).exists():
                    candidate = User.objects.get(username__iexact=username.strip())
                    if candidate.status == User.STATUS_INACTIVE:
                        raise ValidationError(
                            "This account has been deactivated. Contact your administrator.",
                            code="inactive",
                        )
                raise ValidationError(self.error_messages["invalid"], code="invalid")
        return cleaned

    def get_user(self):
        return self.user_cache


class UserCreateForm(StyledFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label="Temporary password",
        widget=forms.PasswordInput(attrs={"placeholder": "At least 8 characters"}),
        help_text="The team member can change this later from Account Settings.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat the password"}),
    )

    class Meta:
        model = User
        fields = ["name", "username", "email", "job_title", "phone", "role", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.all()
        self.fields["role"].empty_label = "Select a role"
        self.fields["status"].initial = User.STATUS_ACTIVE

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        if " " in username:
            raise ValidationError("Usernames cannot contain spaces.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "The two passwords do not match.")
            elif len(p1) < 8:
                self.add_error("password1", "Use at least 8 characters.")
            elif p1.isdigit():
                self.add_error("password1", "Use more than just numbers.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "username", "email", "job_title", "phone", "role", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.all()

    def clean_username(self):
        username = self.cleaned_data["username"].strip().lower()
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        # Never allow removing the final administrator.
        if self.instance.pk and self.instance.role and self.instance.role.role_key == "admin":
            new_role = cleaned.get("role")
            new_status = cleaned.get("status")
            if (new_role and new_role.role_key != "admin") or new_status != User.STATUS_ACTIVE:
                admins = User.objects.filter(
                    role__role_key="admin", status=User.STATUS_ACTIVE
                ).exclude(pk=self.instance.pk)
                if not admins.exists():
                    raise ValidationError(
                        "NEXORA needs at least one active administrator. "
                        "Promote another user first."
                    )
        return cleaned


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "email", "job_title", "phone"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("That email is already used by another account.")
        return email


class NexoraPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    """Django's secure password change flow with NEXORA styling."""

    old_password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 8 characters, not entirely numeric.",
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "nx-input"


class PreferencesForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ["items_per_page", "date_format", "notify_followups", "compact_tables"]
        labels = {
            "items_per_page": "Rows per table page",
            "date_format": "Preferred date format",
            "notify_followups": "Show follow-up reminders in my top bar",
            "compact_tables": "Use compact table spacing",
        }


class RolePermissionsForm(forms.Form):
    """Checkbox matrix for editing the permissions of one role."""

    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        from .permissions import PERMISSIONS

        self.role = role
        initial = list(role.permissions or []) if role else []
        for code, label, group in PERMISSIONS:
            self.fields[code] = forms.BooleanField(
                label=label,
                required=False,
                initial=code in initial,
                widget=forms.CheckboxInput(attrs={"class": "nx-check"}),
            )
        self.fields["_groups"] = forms.CharField(required=False, widget=forms.HiddenInput())

    def selected_codes(self):
        from .permissions import ALL_PERMISSION_CODES

        return [code for code in ALL_PERMISSION_CODES if self.cleaned_data.get(code)]
