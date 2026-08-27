from django.contrib import admin, messages

from notifications.utils import notify

from .models import (
    Course, Enrollment, EnrollmentPayment, Assignment, AssignmentSubmission,
    Certificate, CommunityPost, Module, Lesson, LessonResource, LessonProgress,
    Quiz, QuizQuestion, QuizChoice, QuizAttempt, QuizAnswer,
)


class ModuleInline(admin.StackedInline):
    """Lets an admin build a whole locked curriculum — modules, in order —
    right from the Course page."""
    model = Module
    extra = 0
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "level", "duration", "price", "is_published", "module_count")
    list_filter = ("is_published", "level")
    list_editable = ("price", "is_published")
    search_fields = ("title", "summary", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline]
    actions = ["generate_ai_draft_module"]
    change_list_template = "admin/academy/course/change_list.html"
    fieldsets = (
        ("Basic info", {
            "fields": ("title", "slug", "icon", "summary", "price", "is_published"),
        }),
        ("Course detail page", {
            "fields": ("image", "description", "duration", "level", "requirements", "outcomes"),
        }),
        ("Instructor", {
            "fields": ("instructor_name", "instructor_bio"),
        }),
        ("SEO", {
            "fields": ("meta_description",),
            "description": "Leave blank to fall back to the short description above.",
        }),
        ("Legacy", {
            "fields": ("url_name",),
            "classes": ("collapse",),
            "description": "Only used by courses created before Academy 2.0. New courses can leave this blank.",
        }),
    )

    def module_count(self, obj):
        published = obj.modules.filter(status="published").count()
        draft = obj.modules.filter(status="draft").count()
        if draft:
            return f"{published} published, {draft} draft"
        return f"{published} published"
    module_count.short_description = "Modules"

    def generate_ai_draft_module(self, request, queryset):
        """Generates one new draft module (with lessons, a practical
        assignment, and a quiz) per selected course, via the AI course
        generator. Always created as a hidden draft — review it under
        that course's Modules and flip Status to Published when it's
        ready, exactly as instructed: nothing publishes automatically."""
        from .course_generator import (
            CourseGeneratorError, CourseGeneratorNotConfigured,
            generate_course_draft, save_course_draft,
        )

        if not queryset.exists():
            return

        for course in queryset:
            try:
                draft = generate_course_draft(course, num_modules=1)
                modules = save_course_draft(course, draft)
            except CourseGeneratorNotConfigured as exc:
                self.message_user(request, str(exc), messages.WARNING)
                return
            except CourseGeneratorError as exc:
                self.message_user(
                    request, f"{course.title}: {exc}", messages.ERROR,
                )
                continue

            self.message_user(
                request,
                f"{course.title}: generated {len(modules)} draft module(s) — "
                "review and publish them under Modules.",
                messages.SUCCESS,
            )
    generate_ai_draft_module.short_description = "Generate next AI draft module (review before publishing)"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "progress_percent", "enrolled_at")
    list_filter = ("course",)


@admin.register(EnrollmentPayment)
class EnrollmentPaymentAdmin(admin.ModelAdmin):
    """Payment Requests panel: review a student's bank-transfer claim and
    receipt, then approve (unlocks the course) or reject (with a note)."""

    list_display = ("full_name", "course", "amount", "status", "created_at", "reviewed_at")
    list_filter = ("status", "course")
    search_fields = ("full_name", "email", "phone", "reference")
    readonly_fields = ("user", "course", "full_name", "email", "phone", "amount", "reference",
                       "receipt", "created_at", "reviewed_at", "reviewed_by")
    fields = ("user", "course", "full_name", "email", "phone", "amount", "reference", "receipt",
              "status", "admin_note", "created_at", "reviewed_at", "reviewed_by")
    actions = ["approve_payments", "reject_payments"]

    def approve_payments(self, request, queryset):
        count = 0
        for payment in queryset.filter(status="pending"):
            payment.approve(reviewer=request.user)
            notify(
                payment.user,
                f"Your payment for {payment.course.title} has been approved — the course is unlocked!",
                link="/dashboard/", category="academy_update",
            )
            count += 1
        self.message_user(request, f"Approved {count} payment(s) and unlocked the course.", messages.SUCCESS)
    approve_payments.short_description = "Approve selected payments (unlocks course)"

    def reject_payments(self, request, queryset):
        count = 0
        for payment in queryset.filter(status="pending"):
            payment.reject(reviewer=request.user)
            notify(
                payment.user,
                f"We couldn't verify your payment for {payment.course.title}. "
                "Please reach out on WhatsApp with your receipt.",
                link="/dashboard/", category="academy_update",
            )
            count += 1
        self.message_user(request, f"Rejected {count} payment(s).", messages.WARNING)
    reject_payments.short_description = "Reject selected payments"


class AssignmentSubmissionInline(admin.TabularInline):
    model = AssignmentSubmission
    extra = 0
    readonly_fields = ("user", "content", "submitted_at")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "module", "due_date")
    list_filter = ("course", "module")
    inlines = [AssignmentSubmissionInline]


class LessonResourceInline(admin.TabularInline):
    model = LessonResource
    extra = 0


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    show_change_link = True


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    show_change_link = True


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("course", "order", "title", "status", "is_ai_generated")
    list_filter = ("course", "status", "is_ai_generated")
    list_editable = ("status",)
    ordering = ("course", "order")
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("module", "order", "title")
    list_filter = ("module__course",)
    inlines = [LessonResourceInline]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """A module's single locked quiz — students must pass this (score at
    or above pass_percent) to unlock the next module."""
    list_display = ("module", "title", "pass_percent")
    inlines = [QuizQuestionInline]


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 2


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "text")
    inlines = [QuizChoiceInline]


class QuizAnswerInline(admin.TabularInline):
    """Read-only view of exactly what a student picked per question on
    this attempt, alongside the aggregate score above."""
    model = QuizAnswer
    extra = 0
    readonly_fields = ("question", "choice")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "quiz", "score_percent", "passed", "submitted_at")
    list_filter = ("passed", "quiz__module__course")
    readonly_fields = ("user", "quiz", "score_percent", "passed", "submitted_at")
    inlines = [QuizAnswerInline]


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "completed_at")
    list_filter = ("lesson__module__course",)
    readonly_fields = ("user", "lesson", "completed_at")


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    """Grading a submission here is the ONLY way a student's progress moves —
    there is no student-facing 'mark complete' button. Checking 'passed' and
    saving with status=Reviewed recalculates the enrollment's progress and
    issues a certificate automatically once every assignment is passed."""

    list_display = ("user", "assignment", "status", "passed", "submitted_at")
    list_filter = ("status", "passed", "assignment__course")
    list_editable = ("status", "passed")
    readonly_fields = ("user", "assignment", "content", "submitted_at")
    search_fields = ("user__username", "assignment__title")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.status != "reviewed":
            return

        enrollment, _ = Enrollment.objects.get_or_create(user=obj.user, course=obj.assignment.course)
        if obj.passed:
            enrollment.sync_progress()
        else:
            notify(
                obj.user,
                f"Please review this module before trying again — "
                f"\u201c{obj.assignment.title}\u201d needs another attempt.",
                link="/dashboard/", category="academy_update",
            )


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("user", "course", "certificate_id", "issued_at")


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ("user", "content", "created_at")
