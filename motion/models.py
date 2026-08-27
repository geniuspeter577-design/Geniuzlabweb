from django.db import models
from geniuzlab.validators import validate_image_upload


class MotionShowcase(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    thumbnail = models.ImageField(
        upload_to="motion_showcase/", blank=True, null=True, validators=[validate_image_upload]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
