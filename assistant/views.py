import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .engine import get_reply
from .models import AssistantLog

SESSION_KEY = "glab_assistant_ctx"


@require_POST
def ask(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}

    text = (payload.get("message") or "").strip()
    if not text:
        return JsonResponse({
            "reply": "Type a message and I'll help you find your way around.",
            "links": [],
            "quick_replies": [],
            "escalate": False,
        })

    if not request.session.session_key:
        request.session.save()

    user = request.user if request.user.is_authenticated else None

    # Conversation memory lives in the session so the assistant keeps
    # context (what was just discussed, any pending clarifying
    # question, repeated-fallback tracking) across turns within the
    # same visit, without needing a DB round-trip on every message.
    stored_context = request.session.get(SESSION_KEY)
    result = get_reply(user, text, stored_context)

    request.session[SESSION_KEY] = result["context"]
    request.session.modified = True

    AssistantLog.objects.create(
        user=user,
        session_key=request.session.session_key or "",
        message=text[:2000],
        reply=result["reply"][:2000],
        intent=result["intent"],
    )

    return JsonResponse({
        "reply": result["reply"],
        "links": result["links"],
        "quick_replies": result["quick_replies"],
        "escalate": result["escalate"],
        "redirect_url": result.get("redirect_url"),
    })
