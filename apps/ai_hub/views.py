import base64
import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from .chat_provider import ChatGenerationError, ChatProviderNotConfigured, is_chat_configured, stream_chat_reply
from .models import ChatConversation, ChatMessage, GeneratedImage, GeneratedVideo
from .providers import ImageGenerationError, ProviderNotConfigured, get_image_provider
from .video_providers import (
    VideoGenerationError,
    VideoProviderNotConfigured,
    get_video_provider,
)

logger = logging.getLogger("ai_hub")

MAX_PROMPT_LENGTH = 1000
MAX_CHAT_MESSAGE_LENGTH = 4000
MAX_CHAT_HISTORY_MESSAGES = 20


def _read_prompt(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}
    prompt = (payload.get("prompt") or "").strip()
    return prompt[:MAX_PROMPT_LENGTH]


@login_required
def hub_home(request):
    """The AI Hub landing page: one place linking out to every modular
    AI tool (image generator, video generator, the existing chat
    assistant), each showing whether it's actually configured yet."""
    image_provider = get_image_provider()
    video_provider = get_video_provider()
    return render(request, "ai_hub/home.html", {
        "image_provider_name": image_provider.name,
        "image_configured": image_provider.is_configured(),
        "video_provider_name": video_provider.name,
        "video_configured": video_provider.is_configured(),
        "chat_configured": is_chat_configured(),
    })


@login_required
def image_generator(request):
    provider = get_image_provider()
    recent_images = GeneratedImage.objects.filter(user=request.user)[:12]
    return render(request, "ai_hub/image_generator.html", {
        "provider_name": provider.name,
        "configured": provider.is_configured(),
        "recent_images": recent_images,
    })


@login_required
@require_POST
@ratelimit(key="user", rate="20/d", method="POST", block=True)
def image_generate_api(request):
    prompt = _read_prompt(request)
    if not prompt:
        return JsonResponse(
            {"ok": False, "error": "Please enter a prompt describing the image you want."},
            status=400,
        )

    provider = get_image_provider()

    if not provider.is_configured():
        return JsonResponse({
            "ok": False,
            "not_configured": True,
            "error": (
                f"The image generator isn't set up yet — the '{provider.name}' provider "
                "has no API key configured. Ask a site admin to add one to the server's "
                ".env file (see .env.example)."
            ),
        })

    record = GeneratedImage.objects.create(
        user=request.user, prompt=prompt, provider=provider.name, status="pending"
    )

    try:
        result = provider.generate(prompt)
    except ProviderNotConfigured as exc:
        record.status = "failed"
        record.error_message = str(exc)[:500]
        record.save(update_fields=["status", "error_message"])
        return JsonResponse({"ok": False, "not_configured": True, "error": str(exc)})
    except ImageGenerationError as exc:
        record.status = "failed"
        record.error_message = str(exc)[:500]
        record.save(update_fields=["status", "error_message"])
        return JsonResponse({
            "ok": False,
            "error": "Image generation failed. Please try again in a moment.",
        })
    except Exception:
        logger.exception("Unexpected error generating image for user %s", request.user.pk)
        record.status = "failed"
        record.error_message = "unexpected error"
        record.save(update_fields=["status", "error_message"])
        return JsonResponse({"ok": False, "error": "Something went wrong generating the image."})

    if result.get("url"):
        record.image_url = result["url"]
    elif result.get("b64"):
        try:
            record.image.save(
                f"{record.pk}.png", ContentFile(base64.b64decode(result["b64"])), save=False
            )
        except Exception:
            logger.exception("Failed decoding/saving base64 image for record %s", record.pk)
            record.status = "failed"
            record.error_message = "Failed to save generated image."
            record.save(update_fields=["status", "error_message"])
            return JsonResponse({
                "ok": False,
                "error": "Something went wrong saving the generated image.",
            })

    record.status = "done"
    record.save()

    return JsonResponse({"ok": True, "id": record.pk, "image_url": record.display_url})


@login_required
def video_generator(request):
    provider = get_video_provider()
    recent_videos = GeneratedVideo.objects.filter(user=request.user)[:12]
    return render(request, "ai_hub/video_generator.html", {
        "provider_name": provider.name,
        "configured": provider.is_configured(),
        "recent_videos": recent_videos,
    })


@login_required
@require_POST
@ratelimit(key="user", rate="10/d", method="POST", block=True)
def video_generate_api(request):
    prompt = _read_prompt(request)
    if not prompt:
        return JsonResponse(
            {"ok": False, "error": "Please enter a prompt describing the video you want."},
            status=400,
        )

    provider = get_video_provider()

    if not provider.is_configured():
        return JsonResponse({
            "ok": False,
            "not_configured": True,
            "error": (
                f"The video generator isn't set up yet — the '{provider.name}' provider "
                "has no API key configured. Ask a site admin to add one to the server's "
                ".env file (see .env.example)."
            ),
        })

    record = GeneratedVideo.objects.create(
        user=request.user, prompt=prompt, provider=provider.name, status="queued"
    )

    try:
        job_id = provider.start_generation(prompt)
    except VideoProviderNotConfigured as exc:
        record.status = "not_configured"
        record.error_message = str(exc)[:500]
        record.save(update_fields=["status", "error_message"])
        return JsonResponse({"ok": False, "not_configured": True, "error": str(exc)})
    except VideoGenerationError as exc:
        record.status = "failed"
        record.error_message = str(exc)[:500]
        record.save(update_fields=["status", "error_message"])
        return JsonResponse({
            "ok": False,
            "error": "Video generation failed to start. Please try again.",
        })
    except Exception:
        logger.exception("Unexpected error starting video generation for user %s", request.user.pk)
        record.status = "failed"
        record.save(update_fields=["status"])
        return JsonResponse({"ok": False, "error": "Something went wrong starting the video."})

    record.external_job_id = job_id
    record.status = "processing"
    record.save(update_fields=["external_job_id", "status"])

    return JsonResponse({"ok": True, "id": record.pk, "status": record.status})


@login_required
def video_status_api(request, pk):
    """Polled by the frontend every few seconds while a video job is in
    flight — video generation is asynchronous on every provider, so
    there's no single request/response that returns a finished video."""
    record = get_object_or_404(GeneratedVideo, pk=pk, user=request.user)

    if record.status in ("done", "failed", "not_configured"):
        return JsonResponse({
            "ok": True,
            "status": record.status,
            "video_url": record.video_url,
            "error": record.error_message,
        })

    provider = get_video_provider()
    try:
        result = provider.check_status(record.external_job_id)
    except VideoGenerationError as exc:
        record.status = "failed"
        record.error_message = str(exc)[:500]
        record.save(update_fields=["status", "error_message"])
        return JsonResponse({"ok": True, "status": "failed", "error": record.error_message})
    except Exception:
        logger.exception("Unexpected error polling video status for job %s", record.external_job_id)
        return JsonResponse({"ok": True, "status": record.status})

    record.status = result.get("status", record.status)
    if result.get("video_url"):
        record.video_url = result["video_url"]
    record.save(update_fields=["status", "video_url", "updated_at"])

    return JsonResponse({"ok": True, "status": record.status, "video_url": record.video_url})


# ---------------------------------------------------------------------
# AI Chat (OpenAI, streaming, per-user conversation history/memory)
# ---------------------------------------------------------------------

def _read_chat_message(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}
    message = (payload.get("message") or "").strip()
    return message[:MAX_CHAT_MESSAGE_LENGTH]


@login_required
def chat_list(request):
    """Entry point for AI Hub Chat. Like ChatGPT's root route: if the
    user has a conversation already, drop them into the most recent
    one with the sidebar visible; otherwise show the empty state with
    the sidebar (still empty) so "New conversation" is one click away."""
    conversations = ChatConversation.objects.filter(user=request.user)
    latest = conversations.first()
    if latest:
        return redirect("ai_hub_chat_conversation", pk=latest.pk)
    return render(request, "ai_hub/chat.html", {
        "conversation": None,
        "chat_messages": [],
        "conversations": conversations,
        "chat_configured": is_chat_configured(),
    })


@login_required
@require_POST
def chat_new(request):
    """Creates a blank conversation and redirects into it. A POST
    (not GET) so this can't be triggered by link prefetching."""
    conversation = ChatConversation.objects.create(user=request.user)
    return redirect("ai_hub_chat_conversation", pk=conversation.pk)


@login_required
def chat_conversation(request, pk):
    conversation = get_object_or_404(ChatConversation, pk=pk, user=request.user)
    messages = conversation.messages.all()
    conversations = ChatConversation.objects.filter(user=request.user)
    return render(request, "ai_hub/chat.html", {
        "conversation": conversation,
        "chat_messages": messages,
        "conversations": conversations,
        "chat_configured": is_chat_configured(),
    })


@login_required
@require_POST
@ratelimit(key="user", rate="60/h", method="POST", block=True)
def chat_send_api(request, pk):
    """Streams the assistant's reply back as it's generated (Server-Sent
    Events), so the UI can render it as it arrives instead of waiting
    for the full response. Saves both the user's message and the full
    assistant reply once streaming completes, so the thread persists
    as real conversation memory for the next turn."""
    conversation = get_object_or_404(ChatConversation, pk=pk, user=request.user)

    user_text = _read_chat_message(request)
    if not user_text:
        return JsonResponse({"ok": False, "error": "Message can't be empty."}, status=400)

    if not is_chat_configured():
        return JsonResponse({
            "ok": False,
            "not_configured": True,
            "error": (
                "AI Chat isn't set up yet — OPENAI_API_KEY has no value configured. "
                "Ask a site admin to add one to the server's .env file (see .env.example)."
            ),
        })

    ChatMessage.objects.create(conversation=conversation, role="user", content=user_text)

    if not conversation.title:
        conversation.title = user_text[:80]
    conversation.save(update_fields=["title", "updated_at"])

    history = list(
        conversation.messages.order_by("-created_at")[:MAX_CHAT_HISTORY_MESSAGES]
    )[::-1]
    payload_messages = [{"role": m.role, "content": m.content} for m in history]

    def event_stream():
        collected = []
        try:
            for chunk in stream_chat_reply(payload_messages):
                collected.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except ChatProviderNotConfigured as exc:
            yield f"data: {json.dumps({'error': str(exc), 'not_configured': True})}\n\n"
            return
        except ChatGenerationError as exc:
            logger.error("AI Hub chat generation error: %s", exc)
            yield f"data: {json.dumps({'error': 'AI Chat failed to respond. Please try again.'})}\n\n"
            return
        except Exception:
            logger.exception("Unexpected error streaming chat reply for user %s", request.user.pk)
            yield f"data: {json.dumps({'error': 'Something went wrong generating a reply.'})}\n\n"
            return

        full_reply = "".join(collected).strip()
        if full_reply:
            ChatMessage.objects.create(conversation=conversation, role="assistant", content=full_reply)
            conversation.save(update_fields=["updated_at"])

        yield f"data: {json.dumps({'done': True})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_POST
def chat_delete(request, pk):
    conversation = get_object_or_404(ChatConversation, pk=pk, user=request.user)
    conversation.delete()
    return redirect("ai_hub_chat_list")
