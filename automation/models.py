from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import User
from notifications.models import ALL_CATEGORIES


class AutomationSettings(models.Model):
    """Singleton row (always pk=1) holding the global automation config
    editable from the Automation admin screen — no redeploy needed to
    change the send time or pause everything."""

    enabled = models.BooleanField(
        default=True, help_text="Master switch for the daily notification engine."
    )
    send_hour = models.PositiveSmallIntegerField(default=7, help_text="0-23, server local time.")
    send_minute = models.PositiveSmallIntegerField(default=0, help_text="0-59.")
    assistant_enabled = models.BooleanField(
        default=True, help_text="Show the floating AI chat assistant site-wide."
    )
    bible_verse_enabled = models.BooleanField(
        default=True,
        help_text="Master switch for the daily Bible verse notification. Individual "
        "users can still opt out from their own notification preferences.",
    )
    last_run_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Automation Settings"
        verbose_name_plural = "Automation Settings"

    def __str__(self):
        return f"Automation settings (daily @ {self.send_hour:02d}:{self.send_minute:02d})"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def already_ran_today(self):
        return self.last_run_date == timezone.localdate()


class DailyMessageTemplate(models.Model):
    """One recurring daily message, scoped to a role + category. The
    automation engine sends each active template to every matching user
    at most once per calendar day (enforced by NotificationLog)."""

    ROLE_CHOICES = [
        ("student", "Student"),
        ("instructor", "Instructor"),
        ("creative", "Creative"),
        ("customer", "Customer"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    category = models.CharField(max_length=32, choices=ALL_CATEGORIES)
    message = models.CharField(
        max_length=255,
        help_text="You can use {first_name} as a placeholder for personalization.",
    )
    link = models.CharField(max_length=255, blank=True, help_text="Optional relative URL, e.g. /academy/")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["role", "category"]

    def __str__(self):
        return f"[{self.get_role_display()}] {self.get_category_display()}: {self.message[:40]}"

    def render_for(self, user):
        return self.message.format(first_name=user.first_name or user.username)


class NotificationLog(models.Model):
    """One row per (template, user, day) that was actually sent. The
    unique_together constraint is what guarantees notifications never
    duplicate themselves, even if the scheduler runs twice."""

    CHANNEL_CHOICES = [("in_app", "In-app"), ("email", "Email"), ("both", "In-app + Email"), ("none", "Skipped")]
    STATUS_CHOICES = [("sent", "Sent"), ("failed", "Failed")]

    template = models.ForeignKey(DailyMessageTemplate, on_delete=models.CASCADE, related_name="logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="automation_logs")
    date = models.DateField()
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="in_app")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="sent")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("template", "user", "date")
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.template} -> {self.user.username} on {self.date}"


class BibleVerse(models.Model):
    """One verse in the rotation the daily Bible verse feature draws
    from. Kept as plain data (not hardcoded in code) so the pool can be
    edited or expanded from the admin without a redeploy."""

    reference = models.CharField(max_length=60, help_text="e.g. 'Philippians 4:13'")
    text = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reference"]
        verbose_name = "Bible Verse"

    def __str__(self):
        return self.reference


class BibleVerseLog(models.Model):
    """One row per (user, day) the daily verse was actually sent —
    mirrors NotificationLog's role, guaranteeing a user is never sent
    two verses on the same day even if the scheduler runs twice."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bible_verse_logs"
    )
    verse = models.ForeignKey(BibleVerse, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.verse.reference} -> {self.user.username} on {self.date}"


class Broadcast(models.Model):
    """A one-off announcement an admin can push to all users or a
    specific role, from the automation dashboard."""

    TARGET_CHOICES = [("all", "All Users")] + User.ROLE_CHOICES

    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    target_role = models.CharField(max_length=20, choices=TARGET_CHOICES, default="all")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="broadcasts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipient_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Broadcast to {self.get_target_role_display()}: {self.message[:40]}"

    @property
    def is_sent(self):
        return self.sent_at is not None
