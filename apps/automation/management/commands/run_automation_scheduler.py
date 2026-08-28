import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.automation.models import AutomationSettings
from apps.automation.services import run_daily_bible_verse, run_daily_notifications


class Command(BaseCommand):
    """A zero-infrastructure alternative to Celery Beat: a long-running
    process that wakes up every 30 seconds, checks the configured send
    time in AutomationSettings, and triggers the daily run exactly once
    per day. Good fit for small deployments without Redis/Celery.

    In production with Celery available, prefer Celery Beat (see
    geniuzlab/celery.py) instead of running this command — it survives
    process restarts more gracefully and scales across workers. This
    command (or a plain cron entry calling `send_daily_notifications`)
    is documented as the supported fallback.
    """

    help = "Run an in-process scheduler that fires send_daily_notifications and send_daily_bible_verse once a day at the configured time."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            "Automation scheduler started. Checking every 30 seconds. Press Ctrl+C to stop."
        ))
        try:
            while True:
                self._tick()
                time.sleep(30)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Automation scheduler stopped."))

    def _tick(self):
        settings_obj = AutomationSettings.load()

        now = timezone.localtime() if timezone.is_aware(timezone.now()) else timezone.now()
        at_send_time = now.hour == settings_obj.send_hour and now.minute == settings_obj.send_minute

        if settings_obj.enabled and not settings_obj.already_ran_today and at_send_time:
            stats = run_daily_notifications()
            self.stdout.write(self.style.SUCCESS(f"[{now}] Daily automation triggered: {stats}"))

        # Bible verse sending is gated by its own toggle, not by
        # AutomationSettings.enabled/already_ran_today — those belong
        # to the notification-template engine above. BibleVerseLog's
        # per-(user, date) uniqueness already makes repeated calls
        # within the same send-time window harmless.
        if settings_obj.bible_verse_enabled and at_send_time:
            bible_stats = run_daily_bible_verse()
            if not bible_stats.get("skipped"):
                self.stdout.write(self.style.SUCCESS(f"[{now}] Daily Bible verse triggered: {bible_stats}"))
