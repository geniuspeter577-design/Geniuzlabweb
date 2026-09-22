from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponseGone
from django.shortcuts import get_object_or_404, redirect, render

from apps.notifications.utils import notify
from .models import (
    Assignment, AssignmentSubmission, Certificate, CommunityPost,
    Course, Enrollment, EnrollmentPayment, Lesson, LessonProgress, Module,
    Quiz, QuizAnswer, QuizAttempt, ensure_default_courses,
)


def academy_home(request):
    """Every published course, straight from the database — an admin adding,
    editing, or unpublishing a course in the Django admin is reflected here
    immediately, with no template changes required."""
    ensure_default_courses()
    courses = Course.objects.filter(is_published=True)
    return render(request, "pages/academy.html", {"courses": courses})


def course_detail(request, slug):
    """The single reusable course detail page — replaces the old one-HTML-
    file-per-course setup. Every course, old or admin-created, renders here
    by slug: /academy/course/<slug>/."""
    course = get_object_or_404(Course, slug=slug)
    if not course.is_published and not request.user.is_staff:
        raise Http404("Course not found.")

    enrollment = None
    payment_pending = False
    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        if not enrollment:
            payment_pending = EnrollmentPayment.objects.filter(
                user=request.user, course=course, status="pending"
            ).exists()

    return render(request, "academy/course_detail.html", {
        "course": course,
        "requirements": course.requirements_list,
        "outcomes": course.outcomes_list,
        "enrollment": enrollment,
        "payment_pending": payment_pending,
        "has_modules": course.modules.filter(status="published").exists(),
    })


@login_required
def enroll_course(request, slug):
    """Course Details -> Payment. No more instant/free enrollment: a course
    only unlocks once a bank-transfer payment claim is submitted and
    approved by an admin in the Payment Requests panel."""
    course = get_object_or_404(Course, slug=slug)

    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, f"You're already enrolled in {course.title}.")
        return redirect("dashboard")

    if EnrollmentPayment.objects.filter(user=request.user, course=course, status="pending").exists():
        messages.info(request, f"Your payment for {course.title} is already under review.")
        return redirect("dashboard")

    # Unpublished courses can never be freshly enrolled into. Someone who is
    # already enrolled or has a pending claim (checked above) still passes
    # through untouched — this only blocks starting a brand-new enrollment.
    if not course.is_published and not request.user.is_staff:
        raise Http404("Course not found.")

    return redirect("course_payment", slug=course.slug)


@login_required
def course_payment(request, slug):
    """Compatibility entry point for the online course checkout."""
    course = get_object_or_404(Course, slug=slug)
    if not course.is_published and not request.user.is_staff:
        raise Http404("Course not found.")
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, f"You're already enrolled in {course.title}.")
        return redirect("dashboard")
    if request.method == "POST":
        from apps.payments.views import initiate_course_payment
        return initiate_course_payment(request, slug)
    return render(request, "academy/course_payment.html", {"course": course})


@login_required
def submit_payment(request, slug):
    """Legacy manual-payment endpoint retained only for old bookmarks."""
    return HttpResponseGone(
        "Manual payment claims are no longer accepted. Use the online course checkout."
    )


@login_required
def payment_whatsapp_redirect(request, pk):
    """Legacy manual-payment URL; historical records remain preserved."""
    return HttpResponseGone(
        "Manual payment confirmation is no longer available. Use online checkout."
    )


@login_required
def submit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)

    if not Enrollment.objects.filter(user=request.user, course=assignment.course).exists():
        messages.error(request, "You need to enroll in this course first.")
        return redirect("dashboard")

    if assignment.module_id:
        # New LMS courses: the assignment belongs to a module, and that
        # module's own lock (previous module completed) is the gate —
        # there's no separate ordering to check within the module.
        if assignment.module.status != "published" and not request.user.is_staff:
            raise Http404("Assignment not found.")
        if not assignment.module.is_unlocked_for(request.user):
            messages.error(request, "Please complete the earlier module before trying this assignment.")
            return redirect("course_curriculum", slug=assignment.course.slug)
    else:
        # Older, flat-style courses: assignments are locked in order — a
        # student must pass every assignment that comes before this one
        # (by due_date, then creation order). Only ever compared against
        # other module-less assignments, so LMS courses aren't affected.
        ordered = list(
            Assignment.objects.filter(course=assignment.course, module__isnull=True)
            .order_by("due_date", "created_at")
        )
        position = next((i for i, a in enumerate(ordered) if a.pk == assignment.pk), 0)
        prior = ordered[:position]
        if prior:
            passed_ids = set(
                AssignmentSubmission.objects.filter(
                    user=request.user, assignment__in=prior, status="reviewed", passed=True,
                ).values_list("assignment_id", flat=True)
            )
            if len(passed_ids) < len(prior):
                messages.error(request, "Please complete the earlier assignments in this course first.")
                return redirect("dashboard")

    fallback_redirect = (
        redirect("module_detail", pk=assignment.module_id) if assignment.module_id
        else redirect("dashboard")
    )

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if not content:
            messages.error(request, "Please write a submission before sending it.")
            return fallback_redirect

        AssignmentSubmission.objects.update_or_create(
            assignment=assignment, user=request.user,
            defaults={"content": content, "status": "submitted", "passed": None},
        )
        messages.success(request, f"Submission received for \u201c{assignment.title}\u201d.")

    return fallback_redirect


@login_required
def course_curriculum(request, slug):
    """Modules -> Lessons -> Assignment -> Quiz -> Progress -> Certificate.
    A student must be enrolled (payment approved) to see this; each module
    shows locked/unlocked/completed so they can never skip ahead.

    Note on query cost: computes unlock/completion for every module in the
    course in a fixed small number of queries (one per data type), not one
    round-trip per module — Module.is_unlocked_for/is_completed_for are
    convenient for the single-module call sites (module_detail, quiz_take,
    lesson_mark_complete) but looping them here for a whole course would
    cost roughly 4-5 queries per module; a course with a dozen modules
    would otherwise mean 50+ queries just to render this page."""
    course = get_object_or_404(Course, slug=slug)
    enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
    if not enrollment:
        messages.error(request, f"Enroll in {course.title} first to see its curriculum.")
        return redirect("course_payment", slug=course.slug)

    course_modules = list(course.modules.filter(status="published"))
    module_ids = [m.id for m in course_modules]

    lessons_by_module = {}
    for lesson_id, module_id in Lesson.objects.filter(module_id__in=module_ids).values_list("id", "module_id"):
        lessons_by_module.setdefault(module_id, []).append(lesson_id)
    done_lesson_ids = set(
        LessonProgress.objects.filter(
            user=request.user, lesson__module_id__in=module_ids,
        ).values_list("lesson_id", flat=True)
    )

    assignments_by_module = {}
    for a_id, module_id in Assignment.objects.filter(module_id__in=module_ids).values_list("id", "module_id"):
        assignments_by_module.setdefault(module_id, []).append(a_id)
    passed_assignment_ids = set(
        AssignmentSubmission.objects.filter(
            user=request.user, assignment__module_id__in=module_ids,
            status="reviewed", passed=True,
        ).values_list("assignment_id", flat=True)
    )

    quiz_module_ids = set(Quiz.objects.filter(module_id__in=module_ids).values_list("module_id", flat=True))
    passed_quiz_module_ids = set(
        QuizAttempt.objects.filter(
            user=request.user, passed=True, quiz__module_id__in=module_ids,
        ).values_list("quiz__module_id", flat=True)
    )

    completed_map = {}
    for module in course_modules:
        lessons = lessons_by_module.get(module.id, [])
        completed = all(lid in done_lesson_ids for lid in lessons) if lessons else True
        if completed:
            assigns = assignments_by_module.get(module.id, [])
            completed = all(aid in passed_assignment_ids for aid in assigns) if assigns else True
        if completed and module.id in quiz_module_ids:
            completed = module.id in passed_quiz_module_ids
        completed_map[module.id] = completed

    modules = []
    prev_completed = True  # the first module always starts unlocked
    for module in course_modules:
        modules.append({
            "module": module,
            "unlocked": prev_completed,
            "completed": completed_map[module.id],
        })
        prev_completed = completed_map[module.id]

    return render(request, "academy/curriculum.html", {
        "course": course,
        "enrollment": enrollment,
        "modules": modules,
    })


@login_required
def module_detail(request, pk):
    """A single module's lessons, resources, assignment(s) and quiz —
    locked until the previous module is fully completed."""
    module = get_object_or_404(Module, pk=pk)
    course = module.course

    if module.status != "published" and not request.user.is_staff:
        raise Http404("Module not found.")

    if not Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, f"Enroll in {course.title} first.")
        return redirect("course_payment", slug=course.slug)

    if not module.is_unlocked_for(request.user):
        messages.error(request, "Please complete the earlier module before this one.")
        return redirect("course_curriculum", slug=course.slug)

    completed_lesson_ids = set(
        LessonProgress.objects.filter(user=request.user, lesson__module=module).values_list("lesson_id", flat=True)
    )
    lessons = [
        {"lesson": lesson, "completed": lesson.id in completed_lesson_ids}
        for lesson in module.lessons.all()
    ]

    passed_assignment_ids = set(
        AssignmentSubmission.objects.filter(
            user=request.user, assignment__module=module, status="reviewed", passed=True,
        ).values_list("assignment_id", flat=True)
    )
    submitted_assignment_ids = set(
        AssignmentSubmission.objects.filter(
            user=request.user, assignment__module=module,
        ).values_list("assignment_id", flat=True)
    )
    assignments = [
        {
            "assignment": a,
            "passed": a.id in passed_assignment_ids,
            "submitted": a.id in submitted_assignment_ids,
        }
        for a in module.assignments.all()
    ]

    quiz = getattr(module, "quiz", None)
    quiz_passed = quiz and QuizAttempt.objects.filter(quiz=quiz, user=request.user, passed=True).exists()

    return render(request, "academy/module_detail.html", {
        "course": course,
        "module": module,
        "lessons": lessons,
        "assignments": assignments,
        "quiz": quiz,
        "quiz_passed": quiz_passed,
        "completed": module.is_completed_for(request.user),
    })


@login_required
def lesson_mark_complete(request, pk):
    """The one legitimate 'mark complete' action in the LMS — per-lesson,
    not a shortcut on overall course progress. Overall progress only moves
    once sync_progress() re-checks the whole module."""
    lesson = get_object_or_404(Lesson, pk=pk)
    module = lesson.module

    if request.method != "POST":
        return redirect("module_detail", pk=module.pk)

    if module.status != "published" and not request.user.is_staff:
        raise Http404("Lesson not found.")

    if not Enrollment.objects.filter(user=request.user, course=module.course).exists():
        messages.error(request, "Enroll in this course first.")
        return redirect("course_payment", slug=module.course.slug)

    if not module.is_unlocked_for(request.user):
        messages.error(request, "Please complete the earlier module first.")
        return redirect("course_curriculum", slug=module.course.slug)

    LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)

    enrollment, _ = Enrollment.objects.get_or_create(user=request.user, course=module.course)
    enrollment.sync_progress()

    messages.success(request, f"Marked \u201c{lesson.title}\u201d as complete.")
    return redirect("module_detail", pk=module.pk)


@login_required
def quiz_take(request, pk):
    """Shows the module quiz; grading happens on submit. A passing score
    unlocks the next module and recalculates course progress. Failing
    sends the student back to review the module, exactly as specified —
    no penalty beyond needing another attempt."""
    quiz = get_object_or_404(Quiz, pk=pk)
    module = quiz.module

    if module.status != "published" and not request.user.is_staff:
        raise Http404("Quiz not found.")

    if not Enrollment.objects.filter(user=request.user, course=module.course).exists():
        messages.error(request, "Enroll in this course first.")
        return redirect("course_payment", slug=module.course.slug)

    if not module.is_unlocked_for(request.user):
        messages.error(request, "Please complete the earlier module first.")
        return redirect("course_curriculum", slug=module.course.slug)

    questions = list(quiz.questions.prefetch_related("choices"))

    if request.method == "POST":
        correct = 0
        # Resolve each submitted choice ID up front against that question's
        # real choices — never trust the POSTed choice ID belongs to the
        # question it was posted against.
        picked_choices = {}
        for question in questions:
            submitted_choice_id = request.POST.get(f"question_{question.pk}")
            choice = None
            if submitted_choice_id:
                choice = next(
                    (c for c in question.choices.all() if str(c.pk) == submitted_choice_id), None
                )
            picked_choices[question.pk] = choice
            if choice and choice.is_correct:
                correct += 1
        total = len(questions) or 1
        score_percent = round((correct / total) * 100)
        passed = score_percent >= quiz.pass_percent

        attempt = QuizAttempt.objects.create(
            quiz=quiz, user=request.user, score_percent=score_percent, passed=passed,
        )
        QuizAnswer.objects.bulk_create([
            QuizAnswer(attempt=attempt, question=question, choice=picked_choices[question.pk])
            for question in questions
        ])

        if passed:
            enrollment, _ = Enrollment.objects.get_or_create(user=request.user, course=module.course)
            enrollment.sync_progress()
            messages.success(request, f"Quiz passed with {score_percent}%! The next module is unlocked.")
        else:
            messages.error(
                request,
                f"You scored {score_percent}% — please review this module before trying again.",
            )
        return redirect("module_detail", pk=module.pk)

    return render(request, "academy/quiz.html", {
        "course": module.course,
        "module": module,
        "quiz": quiz,
        "questions": questions,
    })


def certificate_detail(request, certificate_id):
    """Public certificate verification page — no login required, since this
    is the link anyone (e.g. an employer) uses to confirm a certificate is
    genuine. Shows the student, course, issue date, certificate ID, a QR
    code, and the verification URL itself."""
    certificate = get_object_or_404(Certificate, certificate_id=certificate_id)
    verification_url = request.build_absolute_uri()
    qr_code_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=220x220&data={quote(verification_url)}"
    )
    return render(request, "academy/certificate.html", {
        "certificate": certificate,
        "verification_url": verification_url,
        "qr_code_url": qr_code_url,
    })


@login_required
def post_to_community(request):
    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            CommunityPost.objects.create(user=request.user, content=content[:500])
            messages.success(request, "Posted to the Academy community.")
        else:
            messages.error(request, "Write something before posting.")
    return redirect("dashboard")


@user_passes_test(lambda u: u.is_active and u.is_staff)
def academy_admin_stats(request):
    """Staff-only Academy administration dashboard (Phase 4, Part 8):
    payments by status, active/completed students, published/draft
    courses, average progress, quiz stats, and certificate count. Read-only
    — every action it points to (approving payments, grading, publishing
    modules) still happens in Django Admin, unchanged."""
    payment_counts = EnrollmentPayment.objects.values("status").annotate(count=Count("id"))
    payments_by_status = {row["status"]: row["count"] for row in payment_counts}

    total_enrollments = Enrollment.objects.count()
    completed_enrollments = Enrollment.objects.filter(progress_percent__gte=100).count()
    active_enrollments = total_enrollments - completed_enrollments
    average_progress = Enrollment.objects.aggregate(avg=Avg("progress_percent"))["avg"] or 0

    courses = Course.objects.annotate(
        published_module_count=Count("modules", filter=Q(modules__status="published"), distinct=True),
        draft_module_count=Count("modules", filter=Q(modules__status="draft"), distinct=True),
        enrollment_count=Count("enrollments", distinct=True),
    ).order_by("title")

    quiz_attempts = QuizAttempt.objects.count()
    quiz_pass_rate = 0
    if quiz_attempts:
        quiz_pass_rate = round(
            QuizAttempt.objects.filter(passed=True).count() / quiz_attempts * 100
        )

    context = {
        "payments_pending": payments_by_status.get("pending", 0),
        "payments_approved": payments_by_status.get("approved", 0),
        "payments_rejected": payments_by_status.get("rejected", 0),
        "active_students": active_enrollments,
        "completed_students": completed_enrollments,
        "published_courses": Course.objects.filter(is_published=True).count(),
        "draft_courses": Course.objects.filter(is_published=False).count(),
        "average_progress": round(average_progress),
        "quiz_attempts": quiz_attempts,
        "quiz_pass_rate": quiz_pass_rate,
        "certificate_count": Certificate.objects.count(),
        "courses": courses,
        "pending_payments_recent": EnrollmentPayment.objects.filter(
            status="pending"
        ).select_related("course", "user")[:8],
    }
    return render(request, "academy/admin_stats.html", context)
