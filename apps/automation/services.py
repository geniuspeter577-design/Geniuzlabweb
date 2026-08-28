"""Core automation logic, shared by the management command, the Celery
task, and the "Run Now" button in the admin dashboard — so there is
exactly one code path that actually sends daily notifications."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.utils import get_preferences_map

from .models import AutomationSettings, BibleVerse, BibleVerseLog, DailyMessageTemplate, NotificationLog

logger = logging.getLogger("automation")


def run_daily_notifications(force=False):
    """Send today's batch of daily notifications, once per user per
    template per day. Safe to call repeatedly — already-sent
    (template, user, date) combinations are skipped via the
    NotificationLog unique constraint, so nothing is ever duplicated.

    Returns a stats dict describing what happened, for logging/testing.
    """
    settings_obj = AutomationSettings.load()
    today = timezone.localdate()

    if not settings_obj.enabled and not force:
        return {"skipped": True, "reason": "automation disabled"}

    if settings_obj.already_ran_today and not force:
        return {"skipped": True, "reason": "already ran today"}

    templates = list(DailyMessageTemplate.objects.filter(is_active=True))
    users = User.objects.filter(is_active=True).exclude(role="admin")

    sent = 0
    skipped_muted = 0
    skipped_duplicate = 0
    emails_sent = 0

    templates_by_role = {}
    for tmpl in templates:
        templates_by_role.setdefault(tmpl.role, []).append(tmpl)

    users = list(users)
    prefs_by_user = get_preferences_map(users)

    for user in users:
        role_templates = templates_by_role.get(user.role, [])
        if not role_templates:
            continue

        pref = prefs_by_user[user.pk]
        if not pref.in_app_enabled and not pref.email_enabled:
            continue

        for tmpl in role_templates:
            if not pref.allows(tmpl.category):
                skipped_muted += 1
                continue

            try:
                NotificationLog.objects.create(template=tmpl, user=user, date=today)
            except IntegrityError:
                skipped_duplicate += 1
                continue

            message = tmpl.render_for(user)

            if pref.in_app_enabled:
                Notification.objects.create(
                    user=user, message=message, link=tmpl.link, category=tmpl.category
                )

            if pref.email_enabled and user.email:
                try:
                    send_mail(
                        subject="GeniuzLab — " + tmpl.get_category_display(),
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                    emails_sent += 1
                except Exception:
                    logger.exception("Failed sending daily notification email to %s", user.email)

            sent += 1

    settings_obj.last_run_date = today
    settings_obj.save(update_fields=["last_run_date", "updated_at"])

    stats = {
        "skipped": False,
        "sent": sent,
        "emails_sent": emails_sent,
        "skipped_muted": skipped_muted,
        "skipped_duplicate": skipped_duplicate,
        "date": str(today),
    }
    logger.info("Daily automation run complete: %s", stats)
    return stats


def _verse_of_the_day(verses, today):
    """Deterministic pick so every user gets the same verse on the same
    calendar day (a real "daily verse"), and the rotation is stable
    even if the job runs more than once. Cycles through the active
    pool by day-of-year."""
    index = today.timetuple().tm_yday % len(verses)
    return verses[index]


def run_daily_bible_verse(force=False):
    """Send today's Bible verse to every user who hasn't opted out.

    Mirrors run_daily_notifications: uses AutomationSettings as the
    master on/off switch, and BibleVerseLog's unique (user, date)
    constraint to guarantee no one is ever sent two verses in one day,
    even if the scheduler fires twice. Per-user opt-out goes through
    the same NotificationPreference.disabled_categories mechanism as
    every other notification category — the "daily_bible_verse"
    category is toggled from the existing notification preferences
    page, so no separate settings UI was needed for that.
    """
    settings_obj = AutomationSettings.load()
    today = timezone.localdate()

    if not settings_obj.bible_verse_enabled and not force:
        return {"skipped": True, "reason": "bible verse automation disabled"}

    verses = list(BibleVerse.objects.filter(is_active=True))
    if not verses:
        return {"skipped": True, "reason": "no active verses configured"}

    verse = _verse_of_the_day(verses, today)

    users = list(User.objects.filter(is_active=True))
    prefs_by_user = get_preferences_map(users)

    sent = 0
    skipped_muted = 0
    skipped_duplicate = 0

    for user in users:
        pref = prefs_by_user[user.pk]
        if not pref.in_app_enabled:
            continue
        if not pref.allows("daily_bible_verse"):
            skipped_muted += 1
            continue

        try:
            BibleVerseLog.objects.create(user=user, verse=verse, date=today)
        except IntegrityError:
            skipped_duplicate += 1
            continue

        Notification.objects.create(
            user=user,
            message=f'"{verse.text}" — {verse.reference}',
            link="",
            category="daily_bible_verse",
        )
        sent += 1

    stats = {
        "skipped": False,
        "sent": sent,
        "skipped_muted": skipped_muted,
        "skipped_duplicate": skipped_duplicate,
        "verse": verse.reference,
        "date": str(today),
    }
    logger.info("Daily Bible verse run complete: %s", stats)
    return stats


def send_broadcast(broadcast):
    """Immediately push a Broadcast to every matching, active user."""
    users = User.objects.filter(is_active=True)
    if broadcast.target_role != "all":
        users = users.filter(role=broadcast.target_role)
    users = list(users)

    prefs_by_user = get_preferences_map(users)

    count = 0
    for user in users:
        pref = prefs_by_user[user.pk]
        if not pref.in_app_enabled:
            continue
        if not pref.allows("broadcast"):
            continue
        Notification.objects.create(
            user=user, message=broadcast.message, link=broadcast.link, category="broadcast"
        )
        count += 1

    broadcast.sent_at = timezone.now()
    broadcast.recipient_count = count
    broadcast.save(update_fields=["sent_at", "recipient_count"])
    return count
