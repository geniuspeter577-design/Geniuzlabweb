from django.conf import settings
from django.db import models

from geniuzlab.validators import validate_chat_attachment


class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        names = ", ".join(u.username for u in self.participants.all())
        return f"Conversation: {names}"

    def other_participant(self, user):
        # Use the prefetched cache when the caller prefetched participants
        # (e.g. the inbox list) to avoid one query per conversation; falls
        # back to a direct query for single-conversation views that didn't.
        if "participants" in getattr(self, "_prefetched_objects_cache", {}):
            for p in self.participants.all():
                if p.pk != user.pk:
                    return p
            return None
        return self.participants.exclude(pk=user.pk).first()

    def last_message(self):
        if "messages" in getattr(self, "_prefetched_objects_cache", {}):
            msgs = list(self.messages.all())
            return msgs[-1] if msgs else None
        return self.messages.last()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    # A message can reply to an earlier one in the same conversation
    # (Telegram/WhatsApp-style quoted reply). Nullable so plain messages
    # are unaffected; SET_NULL so deleting the original doesn't cascade.
    reply_to = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies"
    )

    # Single-file attachment (image or document). Validated the same way
    # as other user uploads in the project (size/type checked in the view).
    attachment = models.FileField(
        upload_to="chat_attachments/%Y/%m/", blank=True, null=True,
        validators=[validate_chat_attachment],
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.text[:40]}"

    def is_image_attachment(self):
        if not self.attachment:
            return False
        return self.attachment.name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))

    def is_video_attachment(self):
        if not self.attachment:
            return False
        return self.attachment.name.lower().endswith((".mp4", ".mov", ".webm", ".m4v", ".avi", ".mkv"))
