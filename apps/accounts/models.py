from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from geniuzlab.validators import validate_image_upload


class User(AbstractUser):
    ROLE_CHOICES = [
        ("customer", "Customer"),
        ("creative", "Creative"),
        ("student", "Student"),
        ("instructor", "Instructor"),
        ("admin", "Admin"),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="customer"
    )
    # AbstractUser's default `email` field has `unique=False`. Password
    # reset and login-adjacent flows are keyed on email, and `register()` /
    # `edit_profile()` already enforce uniqueness at the application level —
    # this adds the matching DB-level constraint so a race between two
    # concurrent requests can no longer create two accounts with the same
    # email. Run `python manage.py find_duplicate_emails` before applying
    # the migration this generates against a database that predates this
    # change, in case any duplicates already exist.
    email = models.EmailField("email address", blank=True, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    # Whether phone/email should be shown publicly on the user's profile
    # and surfaced as Call/Email buttons on their creative listing.
    # Off by default — a user's contact details are private until they
    # opt in.
    phone_is_public = models.BooleanField(default=False)
    email_is_public = models.BooleanField(default=False)

    # Account-level profile & cover photo, shown on the shared Profile page
    # and dashboard header for every role (customer, creative, student...).
    # Separate from CreativeProfile.avatar, which is the photo shown
    # publicly on the Konnect marketplace listing/detail page.
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, validators=[validate_image_upload]
    )
    cover_photo = models.ImageField(
        upload_to="covers/", blank=True, null=True, validators=[validate_image_upload]
    )

    # Updated on every authenticated request by
    # accounts.middleware.PresenceMiddleware. Used to render the online
    # indicator dot in Messages (chat) and connection suggestions, without
    # needing a websocket/presence server.
    last_active = models.DateTimeField(null=True, blank=True)

    @property
    def is_online(self):
        if not self.last_active:
            return False
        return (timezone.now() - self.last_active).total_seconds() < 300

    @property
    def display_avatar_url(self):
        """Prefer the account avatar; creatives fall back to their
        marketplace-facing CreativeProfile photo if they never set one."""
        if self.avatar:
            return self.avatar.url
        creative_profile = getattr(self, "creative_profile", None)
        if creative_profile and creative_profile.avatar:
            return creative_profile.avatar.url
        return None


class CustomerProfile(models.Model):
    """Extra profile info for customer accounts (business/personal, company
    name). Project history and service requests are read from the existing
    konnect.ServiceRequest relation (client=user) rather than duplicated here."""

    PROFILE_TYPE_CHOICES = [
        ("personal", "Personal"),
        ("business", "Business"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile"
    )
    profile_type = models.CharField(max_length=10, choices=PROFILE_TYPE_CHOICES, default="personal")
    company_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_profile_type_display()})"
