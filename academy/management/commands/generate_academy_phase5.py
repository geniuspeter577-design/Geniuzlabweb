"""Phase 5: populate full DRAFT curricula for all four Academy courses.

This command does NOT touch Wallet, VTU, AI Hub, Konnect, auth, payments,
enrollment automation, or the generator's persistence architecture. It only
orchestrates repeated calls into the existing academy.course_generator
functions (generate_course_draft / save_course_draft), which already
guarantee status="draft" and is_ai_generated=True on every Module they
create. Nothing here ever calls .publish() or sets status="published".

RESUME: safe to stop (Ctrl+C, crash, rate limit) and re-run. Progress is
read from the database itself (module/lesson/quiz/assignment counts) at
the start of every run, not from a separate checkpoint file, so there is
no state to get out of sync. A human-readable progress log is also
written to var/academy_phase5_progress.json purely so you can see what
happened without querying the DB — it is not read back on resume.

DUPLICATE PROTECTION: before saving a batch of AI-generated modules, any
module whose title matches (case-insensitively) a module already saved
for that course is dropped and the batch is retried. The AI is also told
the existing module titles up front so it doesn't repeat itself. The
capstone Assignment and per-module Assignment/Quiz are each created at
most once per module/course by construction — Quiz is a OneToOne on
Module, and the capstone check is an explicit exists() guard.

Requires, in the real deployment environment (NOT this sandbox):
  - a working DB with migrations applied
  - OPENAI_API_KEY set (see academy/course_generator.py: is_configured())
  - network access to api.openai.com

Usage:
  python manage.py generate_academy_phase5
  python manage.py generate_academy_phase5 --resume
  python manage.py generate_academy_phase5 --courses graphic-design,web-development
  python manage.py generate_academy_phase5 --target-modules 10
  python manage.py generate_academy_phase5 --dry-run
"""

import json
import logging
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from academy.course_generator import (
    CourseGeneratorError,
    CourseGeneratorNotConfigured,
    generate_course_draft,
    is_configured,
    save_course_draft,
)
from academy.models import Assignment, Course, ensure_default_courses

logger = logging.getLogger("academy")

ALL_SLUGS = ["graphic-design", "video-editing", "web-development", "ai-productivity"]
MAX_DUPLICATE_RETRIES = 3
PROGRESS_LOG_PATH = Path(settings.BASE_DIR) / "var" / "academy_phase5_progress.json"

# Course-specific capstone briefs. The capstone is saved as a draft
# Assignment attached to the course (module=None) so it shows up as the
# course's final project, distinct from per-module practicals.
CAPSTONES = {
    "graphic-design": (
        "Capstone: Full Brand Identity Package",
        "Combine everything from the course into one deliverable: design a logo, a "
        "business card, a social media post, and a flyer, all for the same made-up "
        "brand, using one consistent colour palette and typography choice across all "
        "four pieces. Submit the four files plus a short write-up explaining your "
        "brand's main message and why your design choices support it.",
    ),
    "video-editing": (
        "Capstone: Short Promotional Video, Start to Finish",
        "Combine everything from the course into one deliverable: shoot or source "
        "footage, edit a 60-90 second promotional video for a made-up brand or event, "
        "including cuts, transitions, colour grading, at least one motion graphic "
        "element, and background music with levels balanced against any dialogue. "
        "Submit the final export plus a short write-up of your editing decisions.",
    ),
    "web-development": (
        "Capstone: Personal Portfolio Website",
        "Combine everything from the course into one deliverable: build and deploy a "
        "responsive multi-section portfolio website (home, about, projects, contact "
        "form) using HTML, CSS and JavaScript, with at least one backend-connected "
        "feature (e.g. the contact form actually storing or sending submissions). "
        "Submit the live link plus your repository.",
    ),
    "ai-productivity": (
        "Capstone: End-to-End AI Automation Workflow",
        "Combine everything from the course into one deliverable: design and document "
        "a real productivity or business workflow that uses at least two different AI "
        "tools together (e.g. drafting, summarizing, or scheduling), including your "
        "prompt templates and the before/after time saved. Submit the workflow "
        "documentation plus one worked example of it running end to end.",
    ),
}


class Command(BaseCommand):
    help = (
        "Phase 5: generates 8-12 modules of full DRAFT curriculum (4-8 lessons, "
        "1 practical assignment, 1 ten-question quiz per module) for each Academy "
        "course, plus one capstone project per course. Never publishes anything. "
        "Safe to stop and re-run — resumes from whatever is already in the DB."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--courses", default=None,
            help=f"Comma-separated course slugs to run (default: all of {ALL_SLUGS}).",
        )
        parser.add_argument(
            "--target-modules", type=int, default=10,
            help="Total modules to have on the course after this run (8-12 recommended). Default 10.",
        )
        parser.add_argument(
            "--modules-per-call", type=int, default=2,
            help="How many modules to request per OpenAI call (keeps responses reliably parseable). Default 2.",
        )
        parser.add_argument(
            "--resume", action="store_true",
            help="Explicit resume mode. Functionally identical to a plain re-run (progress is "
                 "always read from the DB), but prints what's already done vs. what's left "
                 "before doing anything, so you can confirm before it spends API calls.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print the plan (courses, how many modules would be requested) without calling the API.",
        )

    def handle(self, *args, **options):
        ensure_default_courses()

        slugs = (
            [s.strip() for s in options["courses"].split(",")]
            if options["courses"] else ALL_SLUGS
        )
        target_modules = options["target_modules"]
        batch_size = options["modules_per_call"]
        dry_run = options["dry_run"]
        resume = options["resume"]

        if not (8 <= target_modules <= 12):
            self.stdout.write(self.style.WARNING(
                f"--target-modules={target_modules} is outside the requested 8-12 range; proceeding anyway."
            ))

        if not dry_run and not is_configured():
            raise CommandError(
                "OPENAI_API_KEY is not set in this environment — the generator "
                "can't run. Set it and re-run (see academy/course_generator.py)."
            )

        # Resolve courses up front so we can print a resume summary before
        # spending any API calls.
        resolved = []
        for slug in slugs:
            try:
                resolved.append(Course.objects.get(slug=slug))
            except Course.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Unknown course slug: {slug} — skipping."))

        if resume or dry_run:
            self.stdout.write(self.style.HTTP_INFO("\n=== Current state (read from DB) ==="))
            for course in resolved:
                existing = course.modules.count()
                self.stdout.write(
                    f"  {course.title:<20} {existing}/{target_modules} modules "
                    f"({'nothing to do' if existing >= target_modules else f'{target_modules - existing} remaining'})"
                )

        if dry_run:
            self.stdout.write(self.style.SUCCESS("\nDry run — no API calls made, no data written."))
            return

        report = {
            "courses_completed": 0,
            "modules_created": 0,
            "lessons_created": 0,
            "quizzes_created": 0,
            "assignments_created": 0,
            "capstones_created": 0,
            "needs_review": [],
        }
        progress_log = []
        overall_target = target_modules * len(resolved)

        for course in resolved:
            slug = course.slug
            existing_count = course.modules.count()
            to_generate = max(0, target_modules - existing_count)

            logger.info("course_start slug=%s existing=%s target=%s to_generate=%s",
                        slug, existing_count, target_modules, to_generate)
            self.stdout.write(f"\n=== {course.title} ({slug}) — has {existing_count} module(s), generating {to_generate} more ===")

            generated_this_course = 0
            while generated_this_course < to_generate:
                chunk = min(batch_size, to_generate - generated_this_course)
                existing_titles = list(course.modules.values_list("title", flat=True))

                modules = None
                for attempt in range(1, MAX_DUPLICATE_RETRIES + 1):
                    logger.info(
                        "module_batch_request slug=%s attempt=%s/%s requesting=%s",
                        slug, attempt, MAX_DUPLICATE_RETRIES, chunk,
                    )
                    try:
                        draft = generate_course_draft(course, num_modules=chunk, existing_titles=existing_titles)
                    except CourseGeneratorNotConfigured as exc:
                        raise CommandError(str(exc))
                    except CourseGeneratorError as exc:
                        logger.error("generation_failed slug=%s error=%s", slug, exc)
                        self.stderr.write(self.style.ERROR(f"  {course.title}: {exc}"))
                        report["needs_review"].append(f"{slug}: generation error — {exc}")
                        modules = []
                        break

                    lower_existing = {t.lower().strip() for t in existing_titles}
                    original_count = len(draft.get("modules", []))
                    draft["modules"] = [
                        m for m in draft.get("modules", [])
                        if m.get("title", "").lower().strip() not in lower_existing
                    ]
                    dropped = original_count - len(draft["modules"])
                    if dropped:
                        logger.warning(
                            "duplicate_modules_dropped slug=%s dropped=%s attempt=%s",
                            slug, dropped, attempt,
                        )

                    if draft["modules"]:
                        modules = save_course_draft(course, draft)
                        break

                    logger.warning(
                        "batch_all_duplicates slug=%s attempt=%s/%s — retrying",
                        slug, attempt, MAX_DUPLICATE_RETRIES,
                    )
                    modules = []

                if not modules:
                    if not report["needs_review"] or "duplicates" not in report["needs_review"][-1]:
                        msg = f"{slug}: generator kept returning duplicate module titles after {MAX_DUPLICATE_RETRIES} attempts — stopping this course."
                        report["needs_review"].append(msg)
                        self.stderr.write(self.style.ERROR(f"  {msg}"))
                    break

                for m in modules:
                    lesson_count = m.lessons.count()
                    assignment_count = m.assignments.count()
                    quiz = getattr(m, "quiz", None)
                    quiz_count = quiz.questions.count() if quiz is not None else 0

                    report["modules_created"] += 1
                    report["lessons_created"] += lesson_count
                    report["assignments_created"] += assignment_count
                    if quiz is not None:
                        report["quizzes_created"] += 1

                    logger.info(
                        "module_saved slug=%s title=%r lessons=%s quiz_questions=%s assignments=%s",
                        slug, m.title, lesson_count, quiz_count, assignment_count,
                    )
                    self.stdout.write(
                        f"  + '{m.title}' — {lesson_count} lessons, {quiz_count} quiz questions, {assignment_count} assignment(s)"
                    )
                    progress_log.append({
                        "timestamp": timezone.now().isoformat(),
                        "course": slug,
                        "module": m.title,
                        "lessons": lesson_count,
                        "quiz_questions": quiz_count,
                        "assignments": assignment_count,
                    })

                    if lesson_count < 4 or lesson_count > 8:
                        report["needs_review"].append(
                            f"{slug} / '{m.title}': {lesson_count} lessons (spec wants 4-8) — check before publishing."
                        )
                    if quiz is None:
                        report["needs_review"].append(
                            f"{slug} / '{m.title}': no quiz was generated — check before publishing."
                        )
                    elif quiz_count != 10:
                        report["needs_review"].append(
                            f"{slug} / '{m.title}': {quiz_count} quiz questions (spec wants 10) — check before publishing."
                        )
                    if assignment_count == 0:
                        report["needs_review"].append(
                            f"{slug} / '{m.title}': no practical assignment was generated — check before publishing."
                        )

                generated_this_course += len(modules)
                course_pct = min(100, round((existing_count + generated_this_course) / target_modules * 100))
                logger.info("course_progress slug=%s completion_pct=%s", slug, course_pct)
                self.stdout.write(f"  ... {course.title}: {course_pct}% of target modules")
                self._write_progress_log(progress_log)
                time.sleep(1)  # be polite to the API between calls

            # Capstone — one draft Assignment per course, module=None.
            # exists() guard makes this idempotent: re-running never duplicates it.
            title, description = CAPSTONES[slug]
            if not Assignment.objects.filter(course=course, module__isnull=True, title=title).exists():
                Assignment.objects.create(course=course, module=None, title=title, description=description)
                report["capstones_created"] += 1
                logger.info("capstone_created slug=%s title=%r", slug, title)
                self.stdout.write(f"  + capstone created: {title}")
            else:
                self.stdout.write("  = capstone already exists, skipped (duplicate protection)")

            report["courses_completed"] += 1

        self._write_progress_log(progress_log)

        overall_now = sum(c.modules.count() for c in resolved)
        overall_pct = round(overall_now / overall_target * 100) if overall_target else 0
        logger.info("run_complete overall_completion_pct=%s", overall_pct)

        self.stdout.write(self.style.SUCCESS("\n=== Phase 5 generation run complete ==="))
        for k, v in report.items():
            if k != "needs_review":
                self.stdout.write(f"{k}: {v}")
        self.stdout.write(f"overall_completion_pct: {overall_pct}%  ({overall_now}/{overall_target} modules across selected courses)")
        if report["needs_review"]:
            self.stdout.write(self.style.WARNING("\nFlagged for manual review before publishing:"))
            for line in report["needs_review"]:
                self.stdout.write(f"  - {line}")
        self.stdout.write(self.style.WARNING(
            "\nEverything above was saved with status=\"draft\". Nothing was published. "
            "Review and publish manually from Django Admin."
        ))
        self.stdout.write(f"\nProgress log written to {PROGRESS_LOG_PATH}")
        self.stdout.write("If this run stopped early for any reason, just re-run the same "
                           "command (or add --resume) — it will pick up where it left off.")

    def _write_progress_log(self, progress_log):
        try:
            PROGRESS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            PROGRESS_LOG_PATH.write_text(json.dumps(progress_log, indent=2))
        except OSError as exc:
            logger.warning("Could not write progress log to %s: %s", PROGRESS_LOG_PATH, exc)
