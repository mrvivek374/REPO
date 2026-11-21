"""Role, User and preference models for NEXORA."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone

from .permissions import ROLE_DESCRIPTIONS, ROLE_LABELS, ROLE_PRESETS


class Role(models.Model):
    """A named permission bundle assigned to users."""

    ROLE_CHOICES = (
        ("admin", "Administrator"),
        ("manager", "Business Owner / Manager"),
        ("staff", "Staff / Employee"),
    )

    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=60, unique=True)
    role_key = models.CharField(max_length=30, choices=ROLE_CHOICES, unique=True)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"
        ordering = ["role_id"]
        verbose_name = "role"
        verbose_name_plural = "roles"

    def __str__(self):
        return self.role_name

    @property
    def is_locked(self):
        """Administrators always keep every permission."""
        return self.role_key == "admin"

    def has_perm(self, code):
        if self.role_key == "admin":
            return True
        return code in (self.permissions or [])

    def permission_count(self):
        from .permissions import ALL_PERMISSION_CODES

        if self.role_key == "admin":
            return len(ALL_PERMISSION_CODES)
        return len(self.permissions or [])

    @classmethod
    def defaults(cls):
        return [
            {
                "role_key": key,
                "role_name": ROLE_LABELS[key],
                "description": ROLE_DESCRIPTIONS[key],
                "permissions": ROLE_PRESETS[key],
            }
            for key in ("admin", "manager", "staff")
        ]


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("A username is required.")
        user = self.model(username=username.strip().lower(), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        role, _ = Role.objects.get_or_create(
            role_key="admin",
            defaults={
                "role_name": ROLE_LABELS["admin"],
                "description": ROLE_DESCRIPTIONS["admin"],
                "permissions": ROLE_PRESETS["admin"],
            },
        )
        extra_fields.setdefault("role", role)
        extra_fields.setdefault("status", User.STATUS_ACTIVE)
        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser):
    """NEXORA staff account with a role-driven permission set."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    )

    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    username = models.CharField(max_length=60, unique=True, db_index=True)
    email = models.EmailField(max_length=190, unique=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    role = models.ForeignKey(
        Role, on_delete=models.PROTECT, related_name="users", db_column="role_id"
    )
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True
    )
    job_title = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["name", "email"]

    class Meta:
        db_table = "users"
        ordering = ["name"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.name} ({self.username})"

    # ----- Django auth compatibility -------------------------------------
    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def is_staff(self):
        return bool(self.role and self.role.role_key == "admin")

    @property
    def is_superuser(self):
        return self.is_staff

    def has_perm(self, perm, obj=None):
        if not self.is_active:
            return False
        return bool(self.role and self.role.role_key == "admin")

    def has_module_perms(self, app_label):
        return self.has_perm(app_label)

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split(" ")[0] if self.name else self.username

    # ----- UI helpers -----------------------------------------------------
    @property
    def initials(self):
        parts = [part for part in self.name.split() if part]
        if not parts:
            return self.username[:2].upper()
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    @property
    def role_label(self):
        return self.role.role_name if self.role else "Unassigned"

    @property
    def display_status(self):
        return "Active" if self.is_active else "Inactive"

    def can(self, code):
        from .permissions import user_has_perm

        return user_has_perm(self, code)

    def preferences(self):
        cached = getattr(self, "_preference_cache", None)
        if cached is None:
            cached, _ = UserPreference.objects.get_or_create(user=self)
            self._preference_cache = cached
        return cached


class UserPreference(models.Model):
    """Basic per-user application settings."""

    DATE_FORMATS = (
        ("d M Y", "12 Nov 2026"),
        ("d/m/Y", "12/11/2026"),
        ("Y-m-d", "2026-11-12"),
    )
    PER_PAGE_CHOICES = ((8, "8 rows"), (10, "10 rows"), (15, "15 rows"), (25, "25 rows"))

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="preferences_setting"
    )
    items_per_page = models.PositiveSmallIntegerField(default=10, choices=PER_PAGE_CHOICES)
    date_format = models.CharField(max_length=20, default="d M Y", choices=DATE_FORMATS)
    notify_followups = models.BooleanField(default=True)
    compact_tables = models.BooleanField(default=False)

    class Meta:
        db_table = "user_preferences"
        verbose_name = "user preference"
        verbose_name_plural = "user preferences"

    def __str__(self):
        return f"Preferences for {self.user.name}"
