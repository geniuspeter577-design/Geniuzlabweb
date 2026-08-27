import logging

from celery import shared_task

from .models import AutomationSettings
from .services import run_daily_bible_verse, run_daily_notifications

logger = logging.getLogger("automation")


@shared_task
def check_and_send_daily():
    """Runs every minute via Celery Beat. No-ops unless automation is
    enabled, it's the configured send time, and today's batch hasn't
    gone out yet — so this is safe to run as often as you like."""
    from django.utils import timezone

    settings_obj = AutomationSettings.load()
    now = timezone.localtime() if timezone.is_aware(timezone.now()) else timezone.now()
    at_send_time = now.hour == settings_obj.send_hour and now.minute == settings_obj.send_minute

    result = {"skipped": True}
    if settings_obj.enabled and not settings_obj.already_ran_today and at_send_time:
        result = send_daily_notifications_task.run()

    # Bible verse sending has its own toggle and its own duplicate-send
    # guard (BibleVerseLog), so it's triggered independently here rather
    # than being folded into the block above.
    if settings_obj.bible_verse_enabled and at_send_time:
        send_daily_bible_verse_task.run()

    return result


@shared_task
def send_daily_notifications_task(force=False):
    """The actual send — also callable directly (e.g. from the admin
    dashboard's "Run Now" button) via .delay(force=True)."""
    stats = run_daily_notifications(force=force)
    logger.info("send_daily_notifications_task result: %s", stats)
    return stats


@shared_task
def send_daily_bible_verse_task(force=False):
    """Sends today's Bible verse. Also callable directly via
    .delay(force=True)."""
    stats = run_daily_bible_verse(force=force)
    logger.info("send_daily_bible_verse_task result: %s", stats)
    return stats
