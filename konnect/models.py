from django.conf import settings
from django.db import models
from geniuzlab.validators import validate_image_upload, validate_project_media

# Rich category list for individual portfolio projects — deliberately
# separate from CreativeProfile.CATEGORY_CHOICES (which classifies the
# creative's overall discipline). A "Web Development" creative can still
# post a "Logo" project, so projects get their own, more granular list.
PROJECT_CATEGORY_CHOICES = [
    ("logo", "Logo"),
    ("branding", "Branding"),
    ("flyer", "Flyer"),
    ("motion_graphics", "Motion Graphics"),
    ("packaging", "Packaging"),
    ("ui_ux", "UI/UX"),
    ("video_editing", "Video Editing"),
    ("web_development", "Web Development"),
    ("social_media", "Social Media"),
    ("illustration", "Illustration"),
    ("photography", "Photography"),
    ("other", "Other"),
]


class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CreativeProfile(models.Model):
    CATEGORY_CHOICES = [
        ("graphic_design", "Graphic Design"),
        ("video_editing", "Video Editing / Motion"),
        ("web_development", "Web Development"),
        ("ai_productivity", "AI & Productivity"),
        ("other", "Other"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="creative_profile"
    )
    headline = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="other")
    bio = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name="creatives")
    experience_years = models.PositiveIntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(
        upload_to="creative_avatars/", blank=True, null=True, validators=[validate_image_upload]
    )
    is_available = models.BooleanField(default=True)
    availability_note = models.CharField(
        max_length=140, blank=True,
        help_text="e.g. 'Booking from Aug 1' or 'Open to new clients'"
    )
    profile_views = models.PositiveIntegerField(default=0)

    # Services offered — short, comma-style list shown on the public listing
    # (kept as free text rather than a separate model, same pattern as skills).
    services_offered = models.CharField(
        max_length=255, blank=True,
        help_text="e.g. Logo Design, Brand Guidelines, Social Media Kits"
    )

    # Social links
    website_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.get_category_display()}"

    def average_rating(self):
        agg = self.reviews.aggregate(models.Avg("rating"))
        avg = agg["rating__avg"]
        return round(avg, 1) if avg else None

    def review_count(self):
        return self.reviews.count()

    def completed_projects_count(self):
        return self.service_requests.filter(status="completed").count()

    def social_links(self):
        """List of (label, url) tuples for populated social/portfolio links."""
        links = [
            ("Website", self.website_url),
            ("Instagram", self.instagram_url),
            ("Twitter / X", self.twitter_url),
            ("LinkedIn", self.linkedin_url),
        ]
        return [(label, url) for label, url in links if url]


class PortfolioItem(models.Model):
    """A single creative project. Doubles as the 'Project' / feed post
    of the GeniuzLab Creative Social Network: every upload here is what
    shows up in the Home Feed, Discover, and the homepage Graphics
    section."""

    creative = models.ForeignKey(CreativeProfile, on_delete=models.CASCADE, related_name="portfolio_items")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=PROJECT_CATEGORY_CHOICES, default="other")

    # Cover/preview image shown on feed cards. Kept for backwards
    # compatibility with existing templates; auto-filled from the first
    # uploaded gallery image if left blank (see save()).
    image = models.ImageField(
        upload_to="portfolio/", blank=True, null=True, validators=[validate_image_upload]
    )
    link = models.URLField(blank=True)

    views_count = models.PositiveIntegerField(default=0)
    is_reported_hidden = models.BooleanField(
        default=False, help_text="Hidden from feed/discover after moderation review."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.image:
            first_media = self.media.filter(media_type="image").first()
            if first_media and first_media.file:
                PortfolioItem.objects.filter(pk=self.pk).update(image=first_media.file.name)

    def preview_url(self):
        if self.image:
            return self.image.url
        first_media = self.media.filter(media_type="image").first()
        if first_media:
            return first_media.file.url
        return None

    def like_count(self):
        return self.likes.count()

    def comment_count(self):
        return self.comments.count()

    def share_count(self):
        return self.shares.count()

    def is_liked_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.likes.filter(user=user).exists()

    def is_saved_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.saves.filter(user=user).exists()

    def register_view(self, user):
        """Increment the view counter, skipping the creative viewing
        their own project (mirrors CreativeProfile.profile_views)."""
        if user and user.is_authenticated and user == self.creative.user:
            return
        PortfolioItem.objects.filter(pk=self.pk).update(views_count=models.F("views_count") + 1)
        self.refresh_from_db(fields=["views_count"])


class ProjectMedia(models.Model):
    """One image or video in a project's gallery — a project can have
    several, per the 'upload multiple images/videos' requirement."""

    MEDIA_TYPE_CHOICES = [("image", "Image"), ("video", "Video")]

    project = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="portfolio_media/%Y/%m/", validators=[validate_project_media])
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default="image")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.get_media_type_display()} for {self.project.title}"


class ProjectLike(models.Model):
    project = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} likes {self.project.title}"


class ProjectComment(models.Model):
    project = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_comments")
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.text[:40]}"


class ProjectShare(models.Model):
    project = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_shares")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} shared {self.project.title}"


class SavedProject(models.Model):
    """A user's bookmarked project — the Discover/Feed 'Save' action."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_projects")
    project = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "project")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} saved {self.project.title}"


class ProjectReport(models.Model):
    REASON_CHOICES = [
        ("spam", "Spam or misleading"),
        ("copyright", "Copyright / stolen work"),
        ("inappropriate", "Inappropriate content"),
        ("other", "Other"),
    ]

    project = models.ForeignKey(PortfolioItem, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_reports")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default="other")
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report on {self.project.title} by {self.reporter.username}"


class Follow(models.Model):
    """Follow/unfollow between any two users — powers the Home Feed,
    follower/following counts on public profiles, and 'new follower'
    notifications."""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("completed", "Completed"),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests_sent"
    )
    creative = models.ForeignKey(CreativeProfile, on_delete=models.CASCADE, related_name="service_requests")
    message = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # The chat thread this hire's requirements/files get exchanged in —
    # lets job history show "delivered files" for this specific job
    # instead of leaving the customer to dig through raw chat history.
    conversation = models.ForeignKey(
        "chat.Conversation", on_delete=models.SET_NULL, null=True, blank=True, related_name="service_requests"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Request to {self.creative.user.username} from {self.client.username}"

    def delivered_files(self):
        """Attachments exchanged in this job's conversation — what the
        customer/creative should see as 'files delivered for this job'."""
        if not self.conversation_id:
            return []
        return list(
            self.conversation.messages.exclude(attachment="").select_related("sender").order_by("created_at")
        )


class Job(models.Model):
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed")]

    poster = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posted_jobs")
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CreativeProfile.CATEGORY_CHOICES, default="other")
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def applicant_count(self):
        return self.applications.count()


class JobApplication(models.Model):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("shortlisted", "Shortlisted"),
        ("rejected", "Rejected"),
        ("hired", "Hired"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_applications")
    cover_letter = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_at"]
        unique_together = ("job", "applicant")

    def __str__(self):
        return f"{self.applicant.username} -> {self.job.title}"


class CollaborationRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collab_requests_sent"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collab_requests_received"
    )
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"


class SavedCreative(models.Model):
    """A customer's bookmarked creative, for the 'Saved Creatives' dashboard section."""

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_creatives"
    )
    creative = models.ForeignKey(CreativeProfile, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "creative")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.username} saved {self.creative.user.username}"


class Review(models.Model):
    """A client's rating/review of a creative, optionally tied to a specific service request."""

    service_request = models.OneToOneField(
        ServiceRequest, on_delete=models.CASCADE, related_name="review", null=True, blank=True
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_written"
    )
    creative = models.ForeignKey(CreativeProfile, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}\u2605 for {self.creative.user.username} by {self.reviewer.username}"
