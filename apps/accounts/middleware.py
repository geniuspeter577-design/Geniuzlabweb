from django.contrib.auth import get_user_model
from django.utils import timezone


class PresenceMiddleware:
    """Lightweight "online now" tracker.

    Stamps request.user.last_active once every 60s of activity (not on
    every single request, to avoid a DB write per page load). This is
    what powers the online indicator dot in Messages and the Suggested
    Connections cards - no websocket/presence server needed.
    """

    UPDATE_INTERVAL_SECONDS = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # request.user is a django.utils.functional.SimpleLazyObject.
        # Accessing .is_authenticated forces it to resolve to the real
        # user instance (or AnonymousUser), but type(user) still returns
        # SimpleLazyObject itself rather than the wrapped model class -
        # that mismatch is what caused the original AttributeError.
        # get_user_model() gives the correct, concrete model to query
        # against regardless of how "user" is wrapped or proxied.
        user = getattr(request, "user", None)

        if user is not None and getattr(user, "is_authenticated", False):
            self._update_last_active(user)

        return response

    def _update_last_active(self, user):
        """Safely stamp last_active, tolerating races and missing fields."""
        now = timezone.now()
        last_active = getattr(user, "last_active", None)

        stale = (
            last_active is None
            or (now - last_active).total_seconds() > self.UPDATE_INTERVAL_SECONDS
        )
        if not stale:
            return

        User = get_user_model()
        try:
            User.objects.filter(pk=user.pk).update(last_active=now)
        except Exception:
            # Never let presence tracking break the response cycle - e.g.
            # if the user was deleted mid-request, or a custom user model
            # variant doesn't define last_active.
            pass
