from django.conf import settings
from django.db import models

# Canonical notification categories, grouped by the role they apply to.
# Used by both the automation engine (to pick which daily template to send)
# and the user-facing preferences screen (to label the toggle for each one).
STUDENT_CATEGORIES = [
    ("learning_reminder", "Daily learning reminder"),
    ("academy_update", "Academy updates"),
    ("new_course", "New courses"),
    ("ai_tip", "AI learning tips"),
    ("motivation", "Motivation messages"),
]

CREATIVE_CATEGORIES = [
    ("job_opportunity", "New job opportunities"),
    ("client_request", "Client requests"),
    ("portfolio_tip", "Portfolio improvement tips"),
    ("ai_tool", "AI creative tools"),
    ("productivity", "Daily productivity reminders"),
]

CUSTOMER_CATEGORIES = [
    ("hire_suggestion", "Hire creative suggestions"),
    ("recommended_creative", "Recommended creatives"),
    ("platform_update", "Platform updates"),
    ("wallet_reminder", "Wallet reminders"),
    ("promo", "Promotional offers"),
]

SYSTEM_CATEGORIES = [
    ("daily_bible_verse", "Daily Bible verse"),
    ("message", "Messages"),
    ("job", "Jobs"),
    ("application", "Applications"),
    ("collaboration", "Collaborations"),
    ("wallet", "Wallet"),
    ("payment", "Payments"),
    ("vtu", "VTU Orders"),
    ("ai_credit", "AI Credits"),
    ("system", "System Updates"),
    ("broadcast", "Announcements"),
    ("like", "Likes on your work"),
    ("comment", "Comments on your work"),
    ("share", "Shares of your work"),
    ("follow", "New followers"),
]

ALL_CATEGORIES = STUDENT_CATEGORIES + CREATIVE_CATEGORIES + CUSTOMER_CATEGORIES + SYSTEM_CATEGORIES

# Which category group applies to which account role — used by the daily
# automation engine to know which templates to consider for a given user.
ROLE_CATEGORY_GROUPS = {
    "student": STUDENT_CATEGORIES,
    "instructor": STUDENT_CATEGORIES,
    "creative": CREATIVE_CATEGORIES,
    "customer": CUSTOMER_CATEGORIES,
}


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=32, blank=True, choices=ALL_CATEGORIES)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.message[:40]}"


class NotificationPreference(models.Model):
    """Per-user notification settings: a master on/off switch for each
    channel, plus a list of category codes the user has opted out of."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference"
    )
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    disabled_categories = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user.username}"

    def allows(self, category):
        """True if the user hasn't muted this specific category."""
        if not category:
            return True
        return category not in (self.disabled_categories or [])

    def category_choices_for(self, role):
        """The category list relevant to this user's role, for rendering
        the preferences screen — plus the always-visible system ones."""
        return ROLE_CATEGORY_GROUPS.get(role, []) + SYSTEM_CATEGORIES
