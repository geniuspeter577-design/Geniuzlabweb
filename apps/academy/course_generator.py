"""AI-assisted course draft generator (Academy only).

Design goal, same pattern used elsewhere in the project (see
ai_hub/providers.py): this module never lets a missing API key surface as
a 500 — it degrades to a friendly "not set up yet" message instead. It is
intentionally standalone and does not import anything from the ai_hub
app; it only reads the shared OPENAI_API_KEY Django setting that already
exists in geniuzlab/settings.py.

What this produces is a DRAFT ONLY: modules are created with
status="draft" and is_ai_generated=True. Nothing here ever sets a Module
or Course to "published" — that is an explicit admin action in Django
Admin, by design (see PHASE NEXT / Phase 4 instructions: "Nothing should
publish automatically. Admin reviews. Admin edits. Admin publishes.").
"""

import json
import logging
import os

import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger("academy")

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a professional curriculum designer writing lessons for \
complete beginners at GeniuzLab Academy. You never assume prior knowledge. You \
explain difficult concepts in simple, everyday English, using real-life analogies \
before technical terms (for example: comparing HTML to the walls and rooms of a \
house, before defining "markup"). Every lesson you write reads like an instructor \
speaking directly to one student, not like a textbook. You are practical-first: \
every lesson exists to get the student doing something real, not just reading — \
each module's assignment must be a tangible piece of work the student could put in \
a portfolio, not a reflection question or a reading task.

Return ONLY valid JSON (no markdown fences, no commentary) matching this exact shape:

{
  "modules": [
    {
      "title": "string",
      "description": "string, one or two sentences",
      "lessons": [
        {
          "title": "string",
          "content": "string — a complete lesson written in this exact order: \
1) Introduction  2) Concept explanation  3) Why it matters  4) Real-world example  \
5) Step-by-step guide  6) Student exercise  7) Practical task  8) Quiz preparation \
(a short recap of the exact points the quiz will test)  9) Summary. \
Use short paragraphs and plain language throughout. Do not use markdown headers; \
write it as flowing prose with clear paragraph breaks between the sections."
        }
      ],
      "assignment": {
        "title": "string — a hands-on practical task the student DOES, not reads",
        "description": "string — clear instructions for the practical task"
      },
      "quiz": {
        "title": "string",
        "pass_percent": 70,
        "questions": [
          {
            "text": "string",
            "choices": [
              {"text": "string", "is_correct": true},
              {"text": "string", "is_correct": false},
              {"text": "string", "is_correct": false},
              {"text": "string", "is_correct": false}
            ]
          }
        ]
      }
    }
  ]
}

Each module needs 4-8 lessons, exactly one hands-on practical assignment tied to a \
real project (e.g. a flyer, a short video edit, a landing page, a written prompt \
workflow — whatever fits the course), and a quiz with exactly 10 multiple-choice \
questions (exactly one correct choice each) that test understanding of the module's \
concepts rather than rote recall."""


class CourseGeneratorNotConfigured(Exception):
    """OPENAI_API_KEY isn't set — the generator can't run."""


class CourseGeneratorError(Exception):
    """The API call was made but failed or returned something unusable."""


def is_configured():
    return bool(settings.OPENAI_API_KEY)


def _build_user_prompt(course, num_modules, existing_titles=None):
    existing_titles = existing_titles or []
    avoid_block = ""
    if existing_titles:
        titled = "\n".join(f"- {t}" for t in existing_titles)
        avoid_block = (
            "\n\nThis course already has the following modules. Do NOT repeat any of "
            "these topics or reuse a similar title — write genuinely new modules that "
            f"continue the curriculum forward from them:\n{titled}\n"
        )
    return (
        f"Course: {course.title}\n"
        f"Level: {course.get_level_display()}\n"
        f"Short summary: {course.summary}\n"
        f"Full description: {course.description or course.summary}\n"
        f"{avoid_block}\n"
        f"Write {num_modules} new module(s) that would come next in this course's "
        "curriculum, continuing logically from a beginner start toward practical, "
        "portfolio-ready skill. Follow the JSON shape and lesson structure exactly."
    )


def generate_course_draft(course, num_modules=1, model=None, existing_titles=None):
    """Calls OpenAI and returns the parsed draft dict. Raises
    CourseGeneratorNotConfigured or CourseGeneratorError — never lets a
    bad response reach the caller unparsed.

    existing_titles (optional): titles of modules already saved for this
    course, so the model doesn't repeat itself across separate calls
    (e.g. resumed runs). Purely additive — omitting it reproduces the
    prior behavior exactly."""
    if not is_configured():
        raise CourseGeneratorNotConfigured(
            "AI course generation isn't set up yet — add OPENAI_API_KEY to enable it."
        )

    payload = {
        "model": model or os.environ.get("OPENAI_CHAT_MODEL", DEFAULT_MODEL).strip(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(course, num_modules, existing_titles)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }

    try:
        response = requests.post(
            OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        raw_content = data["choices"][0]["message"]["content"]
        draft = json.loads(raw_content)
    except requests.RequestException as exc:
        logger.warning("Academy AI course generator request failed: %s", exc)
        raise CourseGeneratorError("Couldn't reach the AI provider — please try again.") from exc
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.warning("Academy AI course generator returned an unparseable response: %s", exc)
        raise CourseGeneratorError("The AI response wasn't in the expected format.") from exc

    if "modules" not in draft or not isinstance(draft["modules"], list):
        raise CourseGeneratorError("The AI response was missing the expected module list.")

    return draft


@transaction.atomic
def save_course_draft(course, draft):
    """Persists a generated draft as real (but unpublished) Module/Lesson/
    Assignment/Quiz rows. Every module is created as status="draft" and
    is_ai_generated=True — invisible to students until an admin reviews
    and publishes it. Module order continues after whatever modules
    already exist, so this never overwrites or duplicates existing
    curriculum."""
    from .models import Assignment, Lesson, Module, Quiz, QuizChoice, QuizQuestion

    next_order = (course.modules.order_by("-order").values_list("order", flat=True).first() or 0) + 1
    created_modules = []

    for module_data in draft["modules"]:
        module = Module.objects.create(
            course=course,
            title=module_data.get("title", "Untitled module")[:150],
            description=module_data.get("description", ""),
            order=next_order,
            status="draft",
            is_ai_generated=True,
        )
        next_order += 1

        for i, lesson_data in enumerate(module_data.get("lessons", []), start=1):
            Lesson.objects.create(
                module=module,
                title=lesson_data.get("title", f"Lesson {i}")[:150],
                content=lesson_data.get("content", ""),
                order=i,
            )

        assignment_data = module_data.get("assignment")
        if assignment_data:
            Assignment.objects.create(
                course=course,
                module=module,
                title=assignment_data.get("title", "Practical task")[:150],
                description=assignment_data.get("description", ""),
            )

        quiz_data = module_data.get("quiz")
        if quiz_data and quiz_data.get("questions"):
            quiz = Quiz.objects.create(
                module=module,
                title=quiz_data.get("title", "Module Quiz")[:150],
                pass_percent=quiz_data.get("pass_percent", 70),
            )
            for j, q_data in enumerate(quiz_data["questions"], start=1):
                question = QuizQuestion.objects.create(
                    quiz=quiz, text=q_data.get("text", ""), order=j,
                )
                for choice_data in q_data.get("choices", []):
                    QuizChoice.objects.create(
                        question=question,
                        text=choice_data.get("text", ""),
                        is_correct=bool(choice_data.get("is_correct")),
                    )

        created_modules.append(module)

    return created_modules
