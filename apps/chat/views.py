from django.contrib import messages as django_messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.notifications.utils import notify

from .models import Conversation, Message

User = get_user_model()

TYPING_TTL_SECONDS = 5  # how long a "typing" signal is considered current


@login_required
def inbox(request):
    query = (request.GET.get("q") or "").strip()

    # Prefetch participants + messages so building conversation_list below
    # doesn't run other_participant()/last_message() as two extra queries
    # per conversation (was 1 + 2N queries for an inbox with N
    # conversations; now a fixed handful regardless of N).
    conversations = request.user.conversations.prefetch_related(
        "participants",
        Prefetch("messages", queryset=Message.objects.select_related("sender").order_by("created_at")),
    )
    conversation_list = [
        {
            "conversation": c,
            "other_user": c.other_participant(request.user),
            "last_message": c.last_message(),
        }
        for c in conversations
    ]
    if query:
        q_lower = query.lower()
        conversation_list = [
            item for item in conversation_list
            if item["other_user"] and (
                q_lower in item["other_user"].username.lower()
                or q_lower in (item["other_user"].get_full_name() or "").lower()
            )
        ]

    # "Search users / creatives / customers" to start a NEW conversation —
    # separate from filtering the existing conversation list above.
    people_results = []
    if query:
        people_results = (
            User.objects.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
            .exclude(pk=request.user.pk)
            .select_related("creative_profile")[:15]
        )

    return render(request, "chat/inbox.html", {
        "conversation_list": conversation_list,
        "query": query,
        "people_results": people_results,
    })


@login_required
def start_conversation(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    if other_user == request.user:
        return redirect("inbox")

    conversation = (
        Conversation.objects.filter(participants=request.user)
        .filter(participants=other_user)
        .first()
    )
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other_user)

    return redirect("conversation_detail", pk=conversation.pk)


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, participants=request.user)

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        attachment = request.FILES.get("attachment")
        reply_to_id = request.POST.get("reply_to")

        reply_to = None
        if reply_to_id:
            reply_to = conversation.messages.filter(pk=reply_to_id).first()

        if text or attachment:
            msg = Message(conversation=conversation, sender=request.user, text=text, reply_to=reply_to)
            if attachment:
                msg.attachment = attachment
                try:
                    msg.full_clean()
                except ValidationError as exc:
                    django_messages.error(request, " ".join(sum(exc.message_dict.values(), [])))
                    return redirect("conversation_detail", pk=pk)
            msg.save()

            recipient = conversation.other_participant(request.user)
            if recipient:
                notify(
                    recipient,
                    f"New message from {request.user.username}",
                    link=f"/chat/{conversation.pk}/",
                    category="message",
                )
        return redirect("conversation_detail", pk=pk)

    conversation.messages.exclude(sender=request.user).update(is_read=True)
    other_user = conversation.other_participant(request.user)
    # select_related sender + reply_to's sender so the template's message
    # loop (msg.sender, msg.reply_to.sender) doesn't run two extra queries
    # per message on the initial page load.
    messages_qs = conversation.messages.select_related("sender", "reply_to__sender")
    return render(request, "chat/conversation.html", {
        "conversation": conversation,
        "other_user": other_user,
        "conversation_messages": messages_qs,
    })


def _typing_cache_key(conversation_id, user_id):
    return f"chat:typing:{conversation_id}:{user_id}"


@login_required
@require_POST
def set_typing(request, pk):
    """Called (throttled) by the client while the user has text in the
    composer. A short-lived cache flag lets the other participant's next
    poll show a 'typing…' indicator without needing websockets."""
    conversation = get_object_or_404(Conversation, pk=pk, participants=request.user)
    cache.set(_typing_cache_key(conversation.pk, request.user.pk), True, timeout=TYPING_TTL_SECONDS)
    return JsonResponse({"ok": True})


@login_required
def poll_conversation(request, pk):
    """Lightweight polling endpoint the conversation page calls every few
    seconds: any messages newer than `after`, whether the other participant
    is currently typing, and their online status — so new messages, seen
    receipts, and the typing indicator all update without a page reload."""
    conversation = get_object_or_404(Conversation, pk=pk, participants=request.user)
    other_user = conversation.other_participant(request.user)

    after_id = request.GET.get("after")
    new_messages = conversation.messages.select_related("sender", "reply_to__sender")
    if after_id:
        try:
            new_messages = new_messages.filter(pk__gt=int(after_id))
        except (TypeError, ValueError):
            pass
    new_messages = list(new_messages.order_by("created_at"))

    # Any of the other participant's messages we're about to show have,
    # by definition, now been seen — mark them read same as the full page load.
    unread_ids = [m.pk for m in new_messages if m.sender_id != request.user.pk and not m.is_read]
    if unread_ids:
        Message.objects.filter(pk__in=unread_ids).update(is_read=True)

    payload_messages = [{
        "id": m.pk,
        "sender_id": m.sender_id,
        "is_mine": m.sender_id == request.user.pk,
        "text": m.text,
        "attachment_url": m.attachment.url if m.attachment else None,
        "attachment_name": (m.attachment.name.rsplit("/", 1)[-1] if m.attachment else None),
        "is_image": m.is_image_attachment(),
        "is_video": m.is_video_attachment(),
        "reply_to_text": (m.reply_to.text[:80] if m.reply_to else None),
        "created_at": m.created_at.strftime("%H:%M"),
        "is_read": m.is_read,
    } for m in new_messages]

    # Own earlier messages may have just been marked "Seen" by the other
    # side even if no new message came in — report the latest read state
    # for the client's own outgoing messages too.
    my_unseen_now_seen = list(
        conversation.messages.filter(sender=request.user, is_read=True)
        .order_by("-created_at")
        .values_list("pk", flat=True)[:50]
    )

    other_typing = False
    if other_user:
        other_typing = bool(cache.get(_typing_cache_key(conversation.pk, other_user.pk)))

    return JsonResponse({
        "messages": payload_messages,
        "read_message_ids": my_unseen_now_seen,
        "other_typing": other_typing,
        "other_online": other_user.is_online if other_user else False,
    })
