from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from assistant.models import AssistantLog

from .models import AutomationSettings, BibleVerseLog, Broadcast, DailyMessageTemplate, NotificationLog
from .services import run_daily_bible_verse, run_daily_notifications, send_broadcast


@staff_member_required
def automation_dashboard(request):
    settings_obj = AutomationSettings.load()
    today = timezone.localdate()

    context = {
        "settings_obj": settings_obj,
        "templates_count": DailyMessageTemplate.objects.filter(is_active=True).count(),
        "sent_today": NotificationLog.objects.filter(date=today).count(),
        "sent_last_7_days": NotificationLog.objects.filter(
            date__gte=today - timezone.timedelta(days=7)
        ).count(),
        "broadcasts": Broadcast.objects.all()[:10],
        "assistant_messages_today": AssistantLog.objects.filter(created_at__date=today).count(),
        "assistant_messages_total": AssistantLog.objects.count(),
        "bible_verses_sent_today": BibleVerseLog.objects.filter(date=today).count(),
    }
    return render(request, "automation/dashboard.html", context)


@require_POST
@staff_member_required
def update_settings(request):
    settings_obj = AutomationSettings.load()
    settings_obj.enabled = request.POST.get("enabled") == "on"
    settings_obj.assistant_enabled = request.POST.get("assistant_enabled") == "on"
    settings_obj.bible_verse_enabled = request.POST.get("bible_verse_enabled") == "on"
    try:
        settings_obj.send_hour = max(0, min(23, int(request.POST.get("send_hour", 7))))
        settings_obj.send_minute = max(0, min(59, int(request.POST.get("send_minute", 0))))
    except ValueError:
        messages.error(request, "Send time must be numeric.")
        return redirect("automation_dashboard")
    settings_obj.save()
    messages.success(request, "Automation settings updated.")
    return redirect("automation_dashboard")


@require_POST
@staff_member_required
def run_now(request):
    stats = run_daily_notifications(force=True)
    messages.success(
        request,
        f"Ran now: {stats.get('sent', 0)} notifications sent "
        f"({stats.get('emails_sent', 0)} emails), "
        f"{stats.get('skipped_duplicate', 0)} already-sent skipped.",
    )
    return redirect("automation_dashboard")


@require_POST
@staff_member_required
def run_bible_verse_now(request):
    stats = run_daily_bible_verse(force=True)
    if stats.get("skipped"):
        messages.warning(request, f"Skipped: {stats['reason']}")
    else:
        messages.success(
            request,
            f"Sent '{stats['verse']}' to {stats['sent']} users, "
            f"{stats.get('skipped_duplicate', 0)} already-sent skipped.",
        )
    return redirect("automation_dashboard")


@require_POST
@staff_member_required
def create_broadcast(request):
    message = request.POST.get("message", "").strip()
    if not message:
        messages.error(request, "Broadcast message can't be empty.")
        return redirect("automation_dashboard")
    Broadcast.objects.create(
        message=message,
        link=request.POST.get("link", "").strip(),
        target_role=request.POST.get("target_role", "all"),
        created_by=request.user,
    )
    messages.success(request, "Broadcast drafted. Send it below when ready.")
    return redirect("automation_dashboard")


@require_POST
@staff_member_required
def send_broadcast_view(request, pk):
    broadcast = get_object_or_404(Broadcast, pk=pk)
    if broadcast.is_sent:
        messages.warning(request, "That broadcast was already sent.")
        return redirect("automation_dashboard")
    count = send_broadcast(broadcast)
    messages.success(request, f"Broadcast sent to {count} users.")
    return redirect("automation_dashboard")
