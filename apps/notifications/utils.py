from .models import Notification, NotificationPreference


def get_or_create_preference(user):
    pref, _ = NotificationPreference.objects.get_or_create(user=user)
    return pref


def get_preferences_map(users):
    """Bulk version of get_or_create_preference for loops over many users
    (daily automation run, broadcasts) — one query to fetch existing
    preferences plus one bulk_create for any missing ones, instead of a
    get_or_create() query per user."""
    users = list(users)
    existing = {
        p.user_id: p
        for p in NotificationPreference.objects.filter(user__in=users)
    }
    missing = [u for u in users if u.pk not in existing]
    if missing:
        NotificationPreference.objects.bulk_create(
            [NotificationPreference(user=u) for u in missing]
        )
        for p in NotificationPreference.objects.filter(user__in=missing):
            existing[p.user_id] = p
    return existing


def notify(user, message, link="", category=""):
    """Small helper other apps can import to push a notification.

    Respects the user's notification preferences: if they've muted the
    given category (or disabled in-app notifications entirely), no
    Notification row is created.
    """
    pref = get_or_create_preference(user)
    if not pref.in_app_enabled:
        return None
    if not pref.allows(category):
        return None
    return Notification.objects.create(user=user, message=message, link=link, category=category)
