from .models import AutomationSettings


def automation_context(request):
    """Exposes the automation settings site-wide so base.html can decide
    whether to render the floating AI assistant widget, without every
    view needing to remember to pass it in."""
    try:
        settings_obj = AutomationSettings.load()
    except Exception:
        # Tables may not exist yet (e.g. before migrations run) — fail
        # open to "assistant off" rather than breaking every page.
        return {"assistant_enabled": False}
    return {"assistant_enabled": settings_obj.assistant_enabled}
