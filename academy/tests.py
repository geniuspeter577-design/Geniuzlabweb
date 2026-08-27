from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from .models import (
    Assignment, AssignmentSubmission, Certificate, Course, Enrollment,
    EnrollmentPayment, Lesson, LessonProgress, Module, Quiz, QuizAnswer,
    QuizAttempt, QuizChoice, QuizQuestion,
)

User = get_user_model()


def make_course(**kwargs):
    defaults = dict(
        title="Test Course", slug="test-course", summary="A course.",
        price=10000, is_published=True,
    )
    defaults.update(kwargs)
    return Course.objects.create(**defaults)


def make_module_with_content(course, order=1, status="published"):
    """Builds one full module: 2 lessons, 1 assignment, 1 quiz with 2
    questions (one correct choice each) -- enough to exercise every path
    without the overhead of the full 4-8/10-question AI-generated shape."""
    module = Module.objects.create(course=course, title=f"Module {order}", order=order, status=status)
    lesson1 = Lesson.objects.create(module=module, title="Lesson 1", content="Intro", order=1)
    lesson2 = Lesson.objects.create(module=module, title="Lesson 2", content="More", order=2)
    assignment = Assignment.objects.create(course=course, module=module, title="Practical Task")
    quiz = Quiz.objects.create(module=module, title="Module Quiz", pass_percent=70)
    for i in range(2):
        q = QuizQuestion.objects.create(quiz=quiz, text=f"Question {i+1}", order=i + 1)
        QuizChoice.objects.create(question=q, text="Correct", is_correct=True)
        QuizChoice.objects.create(question=q, text="Wrong", is_correct=False)
    return module, [lesson1, lesson2], assignment, quiz


class PaymentApprovalTests(TestCase):
    """1. Payment approval creates Enrollment.
    2. Approving the same payment twice does not create duplicate Enrollment."""

    def setUp(self):
        self.student = User.objects.create_user(username="alice", password="pw12345", email="alice@test.com")
        self.admin = User.objects.create_user(username="admin", password="pw12345", is_staff=True, email="admin@test.com")
        self.course = make_course()

    def test_approve_creates_enrollment(self):
        payment = EnrollmentPayment.objects.create(
            user=self.student, course=self.course, full_name="Alice", email="a@x.com",
            phone="0800000000", amount=10000,
        )
        self.assertEqual(Enrollment.objects.count(), 0)
        payment.approve(reviewer=self.admin)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "approved")
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.course).count(), 1)

    def test_double_approval_does_not_duplicate_enrollment(self):
        payment = EnrollmentPayment.objects.create(
            user=self.student, course=self.course, full_name="Alice", email="a@x.com",
            phone="0800000000", amount=10000,
        )
        payment.approve(reviewer=self.admin)
        payment.approve(reviewer=self.admin)  # simulate a retry / double-click
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.course).count(), 1)

    def test_two_separate_payments_for_same_course_still_one_enrollment(self):
        """A second, independently-created payment approval (e.g. an admin
        mistakenly approving two pending claims) must never create a second
        Enrollment row -- get_or_create on (user, course) protects this."""
        p1 = EnrollmentPayment.objects.create(
            user=self.student, course=self.course, full_name="Alice", email="a@x.com",
            phone="0800000000", amount=10000,
        )
        p2 = EnrollmentPayment.objects.create(
            user=self.student, course=self.course, full_name="Alice", email="a@x.com",
            phone="0800000000", amount=10000,
        )
        p1.approve(reviewer=self.admin)
        p2.approve(reviewer=self.admin)
        self.assertEqual(Enrollment.objects.filter(user=self.student, course=self.course).count(), 1)


class CourseAccessTests(TestCase):
    """3. Student can access a published course after approval.
    4. Unpublished modules remain inaccessible.
    5. Published modules are visible.
    6. Lessons are available."""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(username="bob", password="pw12345", email="bob@test.com")
        self.course = make_course(slug="access-course")
        self.published_module, self.lessons, self.assignment, self.quiz = make_module_with_content(
            self.course, order=1, status="published"
        )
        self.draft_module, _, _, _ = make_module_with_content(self.course, order=2, status="draft")
        self.client.login(username="bob", password="pw12345")

    def test_curriculum_blocked_without_enrollment(self):
        response = self.client.get(reverse("course_curriculum", args=[self.course.slug]))
        self.assertRedirects(response, reverse("course_payment", args=[self.course.slug]))

    def test_curriculum_accessible_after_enrollment(self):
        Enrollment.objects.create(user=self.student, course=self.course)
        response = self.client.get(reverse("course_curriculum", args=[self.course.slug]))
        self.assertEqual(response.status_code, 200)
        module_titles = [m["module"].title for m in response.context["modules"]]
        self.assertIn(self.published_module.title, module_titles)

    def test_draft_module_not_in_curriculum_listing(self):
        Enrollment.objects.create(user=self.student, course=self.course)
        response = self.client.get(reverse("course_curriculum", args=[self.course.slug]))
        module_titles = [m["module"].title for m in response.context["modules"]]
        self.assertNotIn(self.draft_module.title, module_titles)

    def test_draft_module_detail_404s_for_student(self):
        Enrollment.objects.create(user=self.student, course=self.course)
        response = self.client.get(reverse("module_detail", args=[self.draft_module.pk]))
        self.assertEqual(response.status_code, 404)

    def test_published_module_detail_accessible_with_lessons(self):
        Enrollment.objects.create(user=self.student, course=self.course)
        response = self.client.get(reverse("module_detail", args=[self.published_module.pk]))
        self.assertEqual(response.status_code, 200)
        returned_lesson_ids = {row["lesson"].id for row in response.context["lessons"]}
        self.assertEqual(returned_lesson_ids, {l.id for l in self.lessons})


class QuizAndProgressTests(TestCase):
    """7. Quiz exists with questions.
    8. Starting a quiz creates QuizAttempt.
    9. Submitting a quiz grades the attempt.
    10. Completing a lesson updates progress.
    11. Progress percentage changes correctly.
    12. Assignment submission works.
    13. Course completion/certificate logic still works."""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(username="carol", password="pw12345", email="carol@test.com")
        self.admin = User.objects.create_user(username="admin2", password="pw12345", is_staff=True, email="admin2@test.com")
        self.course = make_course(slug="progress-course")
        self.module, self.lessons, self.assignment, self.quiz = make_module_with_content(
            self.course, order=1, status="published"
        )
        self.enrollment = Enrollment.objects.create(user=self.student, course=self.course)
        self.client.login(username="carol", password="pw12345")

    def test_quiz_has_questions(self):
        self.assertEqual(self.quiz.questions.count(), 2)
        for question in self.quiz.questions.all():
            self.assertEqual(question.choices.filter(is_correct=True).count(), 1)

    def test_lesson_complete_updates_progress(self):
        self.assertEqual(self.enrollment.progress_percent, 0)
        self.client.post(reverse("lesson_mark_complete", args=[self.lessons[0].pk]))
        self.assertTrue(
            LessonProgress.objects.filter(user=self.student, lesson=self.lessons[0]).exists()
        )
        # Module isn't done yet (2nd lesson + assignment + quiz still pending)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.progress_percent, 0)

    def test_taking_quiz_creates_attempt_and_grades_it(self):
        questions = list(self.quiz.questions.all())
        post_data = {f"question_{q.pk}": q.choices.get(is_correct=True).pk for q in questions}
        self.assertEqual(QuizAttempt.objects.count(), 0)
        response = self.client.post(reverse("quiz_take", args=[self.quiz.pk]), post_data)
        self.assertEqual(response.status_code, 302)
        attempt = QuizAttempt.objects.get(user=self.student, quiz=self.quiz)
        self.assertEqual(attempt.score_percent, 100)
        self.assertTrue(attempt.passed)

    def test_answers_are_recorded_per_question(self):
        questions = list(self.quiz.questions.all())
        chosen = {q.pk: q.choices.get(is_correct=False) for q in questions}
        post_data = {f"question_{pk}": choice.pk for pk, choice in chosen.items()}
        self.client.post(reverse("quiz_take", args=[self.quiz.pk]), post_data)

        attempt = QuizAttempt.objects.get(user=self.student, quiz=self.quiz)
        self.assertEqual(QuizAnswer.objects.filter(attempt=attempt).count(), len(questions))
        for question in questions:
            saved = QuizAnswer.objects.get(attempt=attempt, question=question)
            self.assertEqual(saved.choice_id, chosen[question.pk].pk)
            self.assertFalse(saved.is_correct)

    def test_unanswered_question_records_null_choice(self):
        questions = list(self.quiz.questions.all())
        # Leave every question blank
        self.client.post(reverse("quiz_take", args=[self.quiz.pk]), {})
        attempt = QuizAttempt.objects.get(user=self.student, quiz=self.quiz)
        self.assertEqual(attempt.score_percent, 0)
        for question in questions:
            saved = QuizAnswer.objects.get(attempt=attempt, question=question)
            self.assertIsNone(saved.choice)

    def test_failing_quiz_does_not_pass(self):
        questions = list(self.quiz.questions.all())
        # Answer nothing correctly
        post_data = {f"question_{q.pk}": q.choices.get(is_correct=False).pk for q in questions}
        self.client.post(reverse("quiz_take", args=[self.quiz.pk]), post_data)
        attempt = QuizAttempt.objects.get(user=self.student, quiz=self.quiz)
        self.assertEqual(attempt.score_percent, 0)
        self.assertFalse(attempt.passed)

    def test_assignment_submission_works(self):
        response = self.client.post(
            reverse("submit_assignment", args=[self.assignment.pk]), {"content": "My work"}
        )
        self.assertEqual(response.status_code, 302)
        submission = AssignmentSubmission.objects.get(user=self.student, assignment=self.assignment)
        self.assertEqual(submission.content, "My work")
        self.assertEqual(submission.status, "submitted")

    def test_full_module_completion_awards_certificate(self):
        # Complete both lessons
        for lesson in self.lessons:
            self.client.post(reverse("lesson_mark_complete", args=[lesson.pk]))

        # Submit and admin-approve the assignment
        self.client.post(reverse("submit_assignment", args=[self.assignment.pk]), {"content": "Done"})
        submission = AssignmentSubmission.objects.get(user=self.student, assignment=self.assignment)
        submission.status = "reviewed"
        submission.passed = True
        submission.save()
        self.enrollment.sync_progress()

        # Pass the quiz
        questions = list(self.quiz.questions.all())
        post_data = {f"question_{q.pk}": q.choices.get(is_correct=True).pk for q in questions}
        self.client.post(reverse("quiz_take", args=[self.quiz.pk]), post_data)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.progress_percent, 100)
        self.assertIsNotNone(self.enrollment.completed_at)
        self.assertTrue(Certificate.objects.filter(user=self.student, course=self.course).exists())

    def test_second_module_locked_until_first_is_completed(self):
        second_module, second_lessons, _, _ = make_module_with_content(
            self.course, order=2, status="published"
        )
        self.assertFalse(second_module.is_unlocked_for(self.student))
        response = self.client.get(reverse("module_detail", args=[second_module.pk]))
        self.assertRedirects(response, reverse("course_curriculum", args=[self.course.slug]))


class IdempotentAutomationTests(TestCase):
    """14. Re-running automation does not duplicate content."""

    def setUp(self):
        self.course = make_course(slug="idempotent-course")

    def test_ensure_default_courses_is_idempotent(self):
        from .models import ensure_default_courses
        ensure_default_courses()
        first_count = Course.objects.count()
        ensure_default_courses()
        second_count = Course.objects.count()
        self.assertEqual(first_count, second_count)

    def test_seed_starter_modules_populates_all_four_courses_and_is_idempotent(self):
        from io import StringIO
        from django.core.management import call_command
        from .models import ensure_default_courses

        ensure_default_courses()
        call_command("seed_showcase_lms_module", stdout=StringIO())
        call_command("seed_starter_modules", stdout=StringIO())

        for slug in ["graphic-design", "video-editing", "web-development", "ai-productivity"]:
            course = Course.objects.get(slug=slug)
            self.assertGreaterEqual(
                course.modules.filter(status="published").count(), 1,
                f"{slug} should have at least one published module",
            )

        module_count_first_run = Module.objects.count()
        lesson_count_first_run = Lesson.objects.count()

        # Re-running must not duplicate anything.
        call_command("seed_showcase_lms_module", stdout=StringIO())
        call_command("seed_starter_modules", stdout=StringIO())

        self.assertEqual(Module.objects.count(), module_count_first_run)
        self.assertEqual(Lesson.objects.count(), lesson_count_first_run)

    def test_save_course_draft_never_publishes_and_is_additive(self):
        from .course_generator import save_course_draft

        draft = {
            "modules": [
                {
                    "title": "Intro Module",
                    "description": "Getting started.",
                    "lessons": [{"title": "L1", "content": "Content"}],
                    "assignment": {"title": "Task", "description": "Do a thing"},
                    "quiz": {
                        "title": "Quiz 1", "pass_percent": 70,
                        "questions": [
                            {"text": "Q1", "choices": [
                                {"text": "A", "is_correct": True},
                                {"text": "B", "is_correct": False},
                            ]}
                        ],
                    },
                }
            ]
        }
        modules = save_course_draft(self.course, draft)
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0].status, "draft")
        self.assertTrue(modules[0].is_ai_generated)

        # Running again with a differently-titled module must not touch
        # or duplicate the first module -- it must add a new one at the
        # next order position.
        draft2 = {
            "modules": [
                {
                    "title": "Second Module",
                    "description": "Next up.",
                    "lessons": [{"title": "L1", "content": "Content"}],
                    "assignment": {"title": "Task 2", "description": "Do another thing"},
                    "quiz": {"title": "Quiz 2", "pass_percent": 70, "questions": []},
                }
            ]
        }
        save_course_draft(self.course, draft2)
        self.assertEqual(Module.objects.filter(course=self.course).count(), 2)
        orders = sorted(Module.objects.filter(course=self.course).values_list("order", flat=True))
        self.assertEqual(orders, [1, 2])
