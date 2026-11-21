"""Authentication backend that accepts either a username or an email."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    """Sign in with ``priya`` or ``priya@nexora.example``."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = (username or kwargs.get("email") or "").strip()
        if not identifier or not password:
            return None
        try:
            user = UserModel.objects.select_related("role").get(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            )
        except UserModel.DoesNotExist:
            UserModel().set_password(password)  # equalise timing
            return None
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        return getattr(user, "is_active", False)
