from django.conf import settings
from django.db import models


class GeneratedImage(models.Model):
    """One image-generation request and its result. Kept even when it
    fails so a user's history and the admin screen show the full
    picture, not just successes."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_images"
    )
    prompt = models.CharField(max_length=1000)
    provider = models.CharField(max_length=40, help_text="Which provider handled this request, e.g. 'openai'.")
    model_name = models.CharField(max_length=80, blank=True)
    image = models.ImageField(upload_to="ai_hub/images/%Y/%m/", blank=True, null=True)
    image_url = models.URLField(
        blank=True,
        max_length=1000,
        help_text="Used when the provider returns a hosted URL instead of raw image bytes.",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.prompt[:40]} ({self.status})"

    @property
    def display_url(self):
        """The single URL templates/JS should use, regardless of whether
        the provider gave us a hosted URL or raw bytes we saved
        ourselves."""
        if self.image:
            return self.image.url
        return self.image_url


class GeneratedVideo(models.Model):
    """One video-generation request. Video providers are async (submit a
    job, poll for completion), so this tracks the external job id and
    status across multiple polls from the frontend."""

    STATUS_CHOICES = [
        ("not_configured", "Provider not configured"),
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_videos"
    )
    prompt = models.CharField(max_length=1000)
    provider = models.CharField(max_length=40, help_text="Which provider handled this request, e.g. 'runway', 'luma'.")
    external_job_id = models.CharField(max_length=200, blank=True)
    video_url = models.URLField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.prompt[:40]} ({self.status})"


class ChatConversation(models.Model):
    """One AI Hub chat thread. A user can have many; each keeps its own
    message history so the assistant has real multi-turn memory within
    a thread without mixing context across unrelated conversations."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_chats"
    )
    title = models.CharField(
        max_length=120, blank=True,
        help_text="Auto-set from the first message; editable later.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Chat #{self.pk}"

    def display_title(self):
        return self.title or "New conversation"


class ChatMessage(models.Model):
    """One message in a ChatConversation. Both the user's turn and the
    assistant's reply are stored as rows (role distinguishes them) so
    the full thread can be replayed to the OpenAI API as conversation
    memory on every subsequent turn."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
