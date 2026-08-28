"""Decorators for temporarily disabling a view without touching its code.

These are applied in urls.py (wrapping the view when building
urlpatterns), not inside the view functions themselves — so vtu/views.py,
subs/views.py, and payments/views.py stay completely untouched and can be
re-enabled later purely by flipping settings.FEATURE_VTU_ENABLED back to
True, with zero code changes.
"""

from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect


def _vtu_enabled():
    return getattr(settings, "FEATURE_VTU_ENABLED", False)


def vtu_feature_gate(view_func):
    """404s the view while FEATURE_VTU_ENABLED is False.

    Used for endpoints that have no sensible "safe" destination to send
    the user back to (VTU purchase pages, subscription checkout, etc.).
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not _vtu_enabled():
            raise Http404("This feature is temporarily unavailable.")
        return view_func(request, *args, **kwargs)
    return wrapped


def vtu_feature_gate_redirect(redirect_to, message=None):
    """Redirects to `redirect_to` (a URL name) while FEATURE_VTU_ENABLED is
    False, instead of 404ing. Used for entry points reachable from a page
    that itself stays live (e.g. wallet funding is reached from the wallet
    page, which keeps working), so users land somewhere useful rather than
    a dead end.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not _vtu_enabled():
                if message:
                    messages.info(request, message)
                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
