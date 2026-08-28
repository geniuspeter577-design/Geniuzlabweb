from django.conf import settings
from django.db import models


class AssistantLog(models.Model):
    """A record of every chat-widget exchange, so admins can monitor
    chatbot activity and quality from the Automation dashboard / admin."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assistant_logs",
    )
    session_key = models.CharField(max_length=40, blank=True)
    message = models.TextField()
    reply = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.user.username if self.user else "anonymous"
        return f"{who}: {self.message[:40]}"
