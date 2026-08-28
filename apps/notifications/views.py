from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Notification, ROLE_CATEGORY_GROUPS, SYSTEM_CATEGORIES
from .utils import get_or_create_preference


@login_required
def notification_list(request):
    # Snapshot the queryset (list()) BEFORE marking unread ones as read.
    # Querysets are lazy and re-fetch on each evaluation with no caching
    # here, so marking is_read=True first and then rendering the same
    # lazy queryset meant the template's "unread" highlight never showed —
    # every notification looked already-read the moment the page loaded.
    notifications = list(request.user.notifications.all())
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect(notification.link or "notifications")


@require_POST
@login_required
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications")


@require_POST
@login_required
def delete_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.delete()
    messages.success(request, "Notification deleted.")
    return redirect("notifications")


@require_POST
@login_required
def delete_all_read(request):
    request.user.notifications.filter(is_read=True).delete()
    messages.success(request, "Read notifications cleared.")
    return redirect("notifications")


@login_required
def preferences(request):
    pref = get_or_create_preference(request.user)
    role_categories = ROLE_CATEGORY_GROUPS.get(request.user.role, [])

    if request.method == "POST":
        pref.in_app_enabled = request.POST.get("in_app_enabled") == "on"
        pref.email_enabled = request.POST.get("email_enabled") == "on"
        selected_categories = request.POST.getlist("category")
        all_codes = [c for c, _ in (role_categories + SYSTEM_CATEGORIES)]
        pref.disabled_categories = [c for c in all_codes if c not in selected_categories]
        pref.save()
        messages.success(request, "Notification preferences updated.")
        return redirect("notification_preferences")

    # SYSTEM_CATEGORIES itself is left untouched (it's shared with the
    # automation engine and the model's stored choices) — this only
    # filters what the preferences screen renders, so the "vtu" toggle
    # isn't shown while VTU is disabled (harmless either way, since no
    # VTU notifications are generated while the feature is off).
    display_categories = SYSTEM_CATEGORIES
    if not getattr(settings, "FEATURE_VTU_ENABLED", False):
        display_categories = [c for c in SYSTEM_CATEGORIES if c[0] != "vtu"]

    return render(
        request,
        "notifications/preferences.html",
        {
            "pref": pref,
            "role_categories": role_categories,
            "system_categories": display_categories,
        },
    )
