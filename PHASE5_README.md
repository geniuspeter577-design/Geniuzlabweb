# Phase 5 — Academy content generator, ready to run locally

Nothing in this run has been executed. This document describes what was
changed and exactly how to run it yourself, since this environment has
no database and no network access to actually generate content.

## What changed

1. **`academy/course_generator.py`** — prompt content only, architecture untouched:
   - lesson structure: 9 parts (Introduction, Concept explanation, Why it
     matters, Real-world example, Step-by-step guide, Student exercise,
     Practical task, Quiz preparation, Summary)
   - 4-8 lessons per module, exactly 10 quiz questions per module
   - explicit "practical-first" instruction -- every assignment must be a
     tangible, portfolio-worthy deliverable, not a reading/reflection task
   - `generate_course_draft()` and `_build_user_prompt()` gained one new
     **optional** argument, `existing_titles` (defaults to `None`, so any
     existing caller behaves exactly as before). When supplied, it's
     listed in the prompt so the model doesn't repeat module topics across
     separate calls (needed for resume/duplicate protection below).
   - `save_course_draft()` -- completely untouched. Still always writes
     `status="draft"`, `is_ai_generated=True`. Nothing publishes anything.

2. **`academy/management/commands/generate_academy_phase5.py`** -- rewritten with:
   - **Logging**: every run logs (via Python's `logging`, logger name
     `"academy"`) which course is active, which module is being requested,
     the lesson/quiz/assignment counts saved for each module, any
     generation failures, and a running completion percentage -- both
     per-course and overall. These also print to your terminal via
     `self.stdout`, so you see them live either way.
   - **Resume**: progress is derived from the database itself
     (`course.modules.count()`) at the start of every run -- there's no
     separate checkpoint file to get out of sync. Stop the command at any
     point (Ctrl+C, crash, API outage) and simply re-run it; it picks up
     exactly where it left off. `--resume` is an explicit flag that prints
     a "here's what's already done, here's what's left" summary before
     doing anything -- functionally the plain re-run does the same thing,
     `--resume` just makes it visible up front.
   - **Duplicate protection**: the model is told the existing module
     titles for the course so it doesn't repeat itself; any module it
     returns anyway with a title matching an existing one (case-insensitive)
     is dropped before saving, and the batch is retried (up to 3 attempts)
     rather than silently saved as a duplicate. Quizzes can't duplicate by
     construction (`Quiz` is a one-to-one on `Module`). The capstone
     assignment is created with an explicit `exists()` check, so re-running
     never creates a second capstone.
   - A human-readable progress log is written to
     `var/academy_phase5_progress.json` after every module (and at the end
     of the run) so you can see exactly what was generated without
     querying the database -- useful for debugging a partial run. It is
     **not** read back on resume; it's diagnostic only, the DB is the
     source of truth.

3. **`geniuzlab/settings.py`** -- one line added to `LOGGING["loggers"]` to
   wire up the `"academy"` logger to the console handler, mirroring the
   existing `"automation"` logger entry that was already there. Without
   this, `logger.info(...)` calls in `course_generator.py` and the new
   command would be silently swallowed by Django's default logging config.

None of the above touches Wallet, VTU, AI Hub, Konnect, authentication,
payment flow, enrollment automation, migrations, or templates.

## How to run it

Prerequisites in your real environment:
- migrations applied (`python manage.py migrate`)
- `OPENAI_API_KEY` set in the environment
- network access to `api.openai.com`

```bash
# 1. See the plan first -- no API calls, no writes
python manage.py generate_academy_phase5 --dry-run

# 2. Run it for real, all 4 courses, ~10 modules each
python manage.py generate_academy_phase5

# 3. If it stops for any reason (rate limit, network blip, Ctrl+C),
#    just run it again -- or be explicit about resuming:
python manage.py generate_academy_phase5 --resume

# Optional: one course at a time, useful for a first test run
python manage.py generate_academy_phase5 --courses graphic-design --target-modules 10
```

Other flags:
- `--target-modules N` -- total modules per course after the run (8-12 recommended, default 10)
- `--modules-per-call N` -- how many modules to request per OpenAI call (default 2; keeping this small keeps each response reliably parseable)
- `--courses slug1,slug2` -- restrict to specific courses (`graphic-design`, `video-editing`, `web-development`, `ai-productivity`)

## Expected runtime and API usage

With defaults (`--target-modules 10`, `--modules-per-call 2`) and starting
from zero modules:

- Per course: 5 API calls (2 modules each) to reach 10 modules
- Total across 4 courses: **20 API calls**
- Each call requests 2 modules x (4-8 lessons + 1 assignment + a 10-question
  quiz) -- this is a large JSON response, so expect roughly 20-60 seconds
  per call depending on OpenAI's load and the `gpt-4o-mini` (default)
  response speed. A full 4-course, 40-module run is roughly **15-35
  minutes** end to end, plus the 1-second pause the command adds between
  calls to stay polite to the API.
- Cost scales with `gpt-4o-mini` token pricing on ~20 large completions;
  check your OpenAI usage dashboard for exact figures since pricing can
  change -- this command doesn't estimate cost for you.
- If a call fails (network blip, rate limit, malformed JSON from the
  model), that course stops and is flagged in the final "needs manual
  review" list; other courses continue. Re-running (or `--resume`) retries
  only what's missing.

## After it runs

Everything generated has `status="draft"`. Review it in Django Admin and
publish manually, module by module -- the command never flips that switch
for you, by design.
