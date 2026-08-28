import uuid

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from geniuzlab.validators import validate_image_upload, validate_receipt_upload


class Course(models.Model):
    LEVEL_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    title = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=10, default="🎓")
    summary = models.CharField(max_length=255, help_text="Short description shown on the course card.")
    url_name = models.CharField(
        max_length=60, blank=True,
        help_text="Legacy field from the old hardcoded course pages. No longer used for "
                   "routing — every course now renders through the single dynamic course "
                   "detail page (by slug). Safe to leave blank on new courses.",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # --- Academy 2.0: CMS-editable fields, so a course is fully database-driven ---
    image = models.ImageField(
        upload_to="course_images/%Y/%m/", blank=True, null=True,
        validators=[validate_image_upload],
        help_text="Used as both the homepage thumbnail and the course detail cover image.",
    )
    description = models.TextField(
        blank=True, help_text="Full description shown on the course detail page.",
    )
    duration = models.CharField(max_length=60, blank=True, help_text="e.g. '6 weeks', '3 months'.")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="beginner")
    requirements = models.TextField(
        blank=True, help_text="One requirement per line, e.g. 'A laptop'.",
    )
    outcomes = models.TextField(
        blank=True, help_text="One learning outcome per line, e.g. 'Build a portfolio website'.",
    )
    instructor_name = models.CharField(max_length=120, blank=True, default="GeniuzLab Instructor Team")
    instructor_bio = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(
        max_length=255, blank=True,
        help_text="SEO meta description. Falls back to the short description if left blank.",
    )
    is_published = models.BooleanField(
        default=True,
        help_text="Unpublished courses are hidden from the academy homepage and detail pages.",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    @property
    def requirements_list(self):
        return [line.strip() for line in self.requirements.splitlines() if line.strip()]

    @property
    def outcomes_list(self):
        return [line.strip() for line in self.outcomes.splitlines() if line.strip()]

    @property
    def seo_description(self):
        return self.meta_description or self.summary


class Enrollment(models.Model):
    """Tracks a student's progress through a course, for the Student Dashboard."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    progress_percent = models.PositiveSmallIntegerField(default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "course")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.progress_percent}%)"

    @property
    def is_completed(self):
        return self.progress_percent >= 100

    def sync_progress(self):
        """Recomputes progress — the only source of truth for advancement.
        Called after an admin reviews a submission, a quiz attempt is
        graded, or a lesson is marked complete. Issues a certificate the
        moment the course is finished.

        Courses with a real Module curriculum (the new LMS structure)
        advance one module at a time — a module only counts once its
        lessons are all marked complete, its assignment(s) are passed,
        and its quiz (if any) is passed. Older courses with no modules
        yet keep advancing purely off graded assignments, exactly as
        before, so nothing that already worked breaks."""
        modules = list(self.course.modules.filter(status="published"))
        if modules:
            total = len(modules)
            completed = sum(1 for m in modules if m.is_completed_for(self.user))
        else:
            total = self.course.assignments.filter(module__isnull=True).count()
            if total == 0:
                return
            completed = AssignmentSubmission.objects.filter(
                user=self.user, assignment__course=self.course, assignment__module__isnull=True,
                status="reviewed", passed=True,
            ).count()

        was_completed = self.progress_percent >= 100
        self.progress_percent = min(100, round((completed / total) * 100)) if total else 0
        if self.progress_percent >= 100 and not self.completed_at:
            self.completed_at = timezone.now()
        self.save()

        if self.progress_percent >= 100 and not was_completed:
            from apps.notifications.utils import notify
            Certificate.objects.get_or_create(user=self.user, course=self.course)
            notify(
                self.user,
                f"Congratulations! You've earned a certificate for {self.course.title}.",
                link="/dashboard/", category="academy_update",
            )


class Module(models.Model):
    """One locked step of a course's curriculum: Module -> Lessons ->
    (optional) Assignment(s) -> (optional) Quiz. A course with no Module
    rows behaves exactly like the old flat course (assignments hang
    straight off it), so existing courses/enrollments are unaffected."""

    STATUS_CHOICES = [
        ("draft", "Draft — hidden from students, admin review needed"),
        ("published", "Published — visible to enrolled students"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=1)
    # Defaults to "published" so every module an admin builds by hand keeps
    # working exactly as before. Only the AI course generator sets new
    # modules to "draft" — nothing it produces is ever visible to a student
    # until an admin reviews and republishes it.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="published")
    is_ai_generated = models.BooleanField(
        default=False,
        help_text="Set automatically by the AI course generator. Review the content, "
                   "edit anything that needs it, then set Status to Published.",
    )

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("course", "order")

    def __str__(self):
        return f"{self.course.title} — Module {self.order}: {self.title}"

    @property
    def is_published(self):
        return self.status == "published"

    def is_unlocked_for(self, user):
        """The first published module is always open once enrolled. Every
        later published module stays locked until the module right before
        it is done — students can never skip ahead. Draft modules never
        factor into lock order — they're invisible to students until an
        admin publishes them."""
        prior = (
            Module.objects.filter(course=self.course, order__lt=self.order, status="published")
            .order_by("-order")
            .first()
        )
        if not prior:
            return True
        return prior.is_completed_for(user)

    def is_completed_for(self, user):
        lessons = list(self.lessons.all())
        if lessons:
            done = set(
                LessonProgress.objects.filter(user=user, lesson__in=lessons).values_list("lesson_id", flat=True)
            )
            if len(done) < len(lessons):
                return False

        assignments = list(self.assignments.all())
        if assignments:
            passed = set(
                AssignmentSubmission.objects.filter(
                    user=user, assignment__in=assignments, status="reviewed", passed=True,
                ).values_list("assignment_id", flat=True)
            )
            if len(passed) < len(assignments):
                return False

        quiz = getattr(self, "quiz", None)
        if quiz and not QuizAttempt.objects.filter(quiz=quiz, user=user, passed=True).exists():
            return False

        return True


class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=150)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.module.title} — {self.title}"


class LessonResource(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="resources")
    title = models.CharField(max_length=150)
    url = models.URLField(blank=True)
    file = models.FileField(upload_to="lesson_resources/%Y/%m/", blank=True, null=True)

    def __str__(self):
        return self.title


class LessonProgress(models.Model):
    """A student marking a lesson as read/watched. This is real,
    per-lesson completion tracking — not the old fake 'Mark 25%
    Complete' shortcut, which never touched overall course progress.
    Overall Enrollment.progress_percent only ever moves via
    sync_progress(), based on whole modules being done."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_entries")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user.username} completed {self.lesson.title}"


class Quiz(models.Model):
    module = models.OneToOneField(Module, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=150, default="Module Quiz")
    pass_percent = models.PositiveSmallIntegerField(default=70)

    def __str__(self):
        return f"Quiz: {self.module.title}"


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:60]


class QuizChoice(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    score_percent = models.PositiveSmallIntegerField(default=0)
    passed = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} ({self.score_percent}%)"


class QuizAnswer(models.Model):
    """The specific choice a student picked for one question on one
    attempt. QuizAttempt already stores the aggregate score/pass-fail —
    this is the per-question record behind that number, so an admin (or
    the student, on a future review screen) can see exactly what was
    answered, not just the final percentage. One row per (attempt,
    question); grading in quiz_take() saves these alongside the
    QuizAttempt in the same request."""

    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="answers")
    choice = models.ForeignKey(
        QuizChoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Null if the student submitted the quiz without answering this question.",
    )

    class Meta:
        unique_together = ("attempt", "question")

    def __str__(self):
        picked = self.choice.text if self.choice else "(no answer)"
        return f"{self.attempt} — Q{self.question.order}: {picked}"

    @property
    def is_correct(self):
        return bool(self.choice and self.choice.is_correct)


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="assignments", null=True, blank=True,
        help_text="Leave blank for older, flat-style courses. Set this to gate the "
                   "assignment behind its module being unlocked.",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.course.title})"


class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ("submitted", "Submitted — awaiting review"),
        ("reviewed", "Reviewed"),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_submissions"
    )
    content = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="submitted")
    grade = models.CharField(max_length=10, blank=True)
    passed = models.BooleanField(
        null=True, blank=True,
        help_text="Set when reviewing: checked = counts toward progress and unlocks the "
                   "next assignment; unchecked = student is sent back to the lesson.",
    )
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("assignment", "user")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.username} -> {self.assignment.title}"


class Certificate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="certificates")
    certificate_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "course")
        ordering = ["-issued_at"]

    def __str__(self):
        return f"Certificate: {self.user.username} - {self.course.title}"


class EnrollmentPayment(models.Model):
    """A student's claim of having paid for a course via manual bank
    transfer. Stays 'pending' until an admin reviews it in the Payment
    Requests panel; approving it unlocks the course by creating the
    Enrollment."""

    STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollment_payments"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollment_payments")
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    receipt = models.FileField(
        upload_to="payment_receipts/%Y/%m/", blank=True, null=True,
        validators=[validate_receipt_upload],
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_enrollment_payments",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} - {self.course.title} ({self.get_status_display()})"

    def approve(self, reviewer=None, note=""):
        """Approving a payment claim is the ONLY step an admin takes —
        everything after this (Enrollment creation, linking student/course/
        payment, marking it active with an enrollment date) happens here
        automatically. Wrapped in a transaction so a crash between marking
        the payment approved and creating the Enrollment can never leave
        one without the other. get_or_create prevents a duplicate
        Enrollment if a payment is somehow approved twice."""
        with transaction.atomic():
            self.status = "approved"
            self.reviewed_at = timezone.now()
            self.reviewed_by = reviewer
            if note:
                self.admin_note = note
            self.save()
            enrollment, _ = Enrollment.objects.get_or_create(user=self.user, course=self.course)
        return enrollment

    def reject(self, reviewer=None, note=""):
        self.status = "rejected"
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        if note:
            self.admin_note = note
        self.save()


class CommunityPost(models.Model):
    """A lightweight academy-wide community feed post."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_posts")
    content = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.content[:40]}"


DEFAULT_COURSES = [
    {"title": "Graphic Design", "slug": "graphic-design", "icon": "🎨",
     "summary": "Branding, flyers, logos and social media design.", "url_name": "graphic_design",
     "price": 25000, "duration": "8 weeks", "level": "beginner",
     "description": "Learn branding, flyers, logos and social media design from the ground "
                     "up, and finish with real client-ready work for your portfolio.",
     "requirements": "A laptop or desktop computer\nAdobe Photoshop or Canva Pro (free trial is fine)",
     "outcomes": "Design a complete brand identity\nCreate social media graphics that convert\n"
                 "Build a professional design portfolio"},
    {"title": "Video Editing", "slug": "video-editing", "icon": "🎬",
     "summary": "Cinematic editing, reels, YouTube and motion graphics.", "url_name": "video_editing",
     "price": 25000, "duration": "8 weeks", "level": "beginner",
     "description": "Learn cinematic editing, reels, YouTube content and motion graphics "
                     "using industry-standard tools and real footage.",
     "requirements": "A laptop capable of running video editing software\nCapCut or Adobe Premiere Pro",
     "outcomes": "Edit cinematic short-form and long-form content\nColor grade and add motion graphics\n"
                 "Deliver client-ready video projects"},
    {"title": "Web Development", "slug": "web-development", "icon": "💻",
     "summary": "Modern websites and web applications.", "url_name": "web_development",
     "price": 35000, "duration": "12 weeks", "level": "intermediate",
     "description": "Build modern, responsive websites and web applications from scratch, "
                     "covering both frontend and backend fundamentals.",
     "requirements": "A laptop\nBasic computer literacy — no prior coding experience required",
     "outcomes": "Build responsive websites with HTML, CSS and JavaScript\n"
                 "Create backend applications and manage databases\n"
                 "Ship real projects for your portfolio"},
    {"title": "AI & Productivity", "slug": "ai-productivity", "icon": "🤖",
     "summary": "AI tools, automation and productivity workflows.", "url_name": "ai_productivity",
     "price": 20000, "duration": "6 weeks", "level": "beginner",
     "description": "Learn to use modern AI tools, automation and productivity workflows to "
                     "work faster and smarter in any field.",
     "requirements": "A laptop or smartphone\nAn internet connection",
     "outcomes": "Use AI tools to automate repetitive work\nBuild productivity workflows\n"
                 "Apply AI effectively in a professional setting"},
]


def ensure_default_courses():
    """Idempotently seeds the four academy course records. Cheap to call on
    every dashboard load — get_or_create is a no-op once rows exist."""
    for data in DEFAULT_COURSES:
        Course.objects.get_or_create(slug=data["slug"], defaults=data)
    return Course.objects.all()
