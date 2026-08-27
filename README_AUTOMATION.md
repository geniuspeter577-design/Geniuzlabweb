# GeniuzLab Automation & Smart Assistant

This adds three apps to the project: `automation` (daily notifications,
scheduling, broadcasts, the daily Bible verse), `assistant` (the floating
AI chat widget), and `ai_hub` (the AI Image/Video Generator tools — see
`ai_hub/providers.py` and `ai_hub/video_providers.py`, and `.env.example`
for the environment variables that configure them).

## 1. Setup

```bash
pip install -r requirements.txt
cp .env.example .env                          # then fill in the keys you have
python manage.py migrate
python manage.py seed_automation_templates   # loads the default daily messages
python manage.py seed_bible_verses           # loads the default Bible verse pool
python manage.py createsuperuser             # if you don't have one yet
```

Then visit `/automation/` while logged in as staff to see the control
center, `/admin/automation/` for raw CRUD on templates/logs/broadcasts/Bible
verses, or `/ai-hub/` for the Image/Video Generator tools.

## 2. Daily notifications — how sending actually happens

Three ways to trigger `send_daily_notifications` (and, alongside it,
`send_daily_bible_verse` — both are triggered by the same scheduler/Celery
tick, each gated by its own `AutomationSettings` toggle), pick whichever
fits your infrastructure:

**Option A — Celery + Celery Beat (recommended for production)**
Requires Redis (or another broker) running.
```bash
celery -A geniuzlab worker -l info
celery -A geniuzlab beat -l info
```
A task checks every minute whether it's the configured send time
(`Automation Settings` in the admin) and hasn't already run today, and
triggers the send. Changing the time in `/automation/` takes effect
immediately — no restart needed.

**Option B — Built-in scheduler (zero extra infrastructure)**
```bash
python manage.py run_automation_scheduler
```
Run this as a long-lived process (e.g. a systemd service or a second
Docker/Render/Railway process). It polls every 30 seconds and fires the
same logic as Celery Beat, just without Redis.

**Option C — System cron**
```
0 7 * * * cd /path/to/project && python manage.py send_daily_notifications
0 7 * * * cd /path/to/project && python manage.py send_daily_bible_verse
```
Simplest option if your host already gives you cron. Note: with this
option, changing the send time in the admin dashboard has no effect —
you'd need to edit the crontab entry too.

All three call the exact same underlying logic (`automation/services.py`),
and notifications are never duplicated: each `(template, user, day)`
combination — and, for the Bible verse, each `(user, day)` combination —
is only ever sent once, enforced at the database level.

## 2b. Daily Bible verse

A separate, independently-toggleable automation living in the same app:

- **Verse pool:** `automation/models.py:BibleVerse`, seeded by
  `python manage.py seed_bible_verses` (idempotent, edit/add more from
  `/admin/automation/bibleverse/` any time).
- **Master on/off switch:** the "Daily Bible verse enabled" toggle on
  `/automation/` (`AutomationSettings.bible_verse_enabled`).
- **Per-user opt-out:** reuses the existing notification preferences page
  — "Daily Bible verse" appears there automatically as its own category
  (`notifications/models.py:SYSTEM_CATEGORIES`), no separate UI was needed.
- **Sending logic:** `automation/services.py:run_daily_bible_verse()`.
  Same verse goes to everyone on a given calendar day (deterministic pick
  by day-of-year), and `BibleVerseLog`'s unique `(user, date)` constraint
  guarantees no one is ever sent two on the same day.
- Triggered by whichever of the three options above you're already using
  for daily notifications — no separate infrastructure required.

## 3. AI chat assistant

Works out of the box with no credentials — it answers using built-in
rule-based logic (hiring, courses, wallet, jobs, VTU, account help, etc.)
and always points the user to a real page on the site.

**Knowledge base (company/founder/services/pricing/FAQs/customer care/
business hours/policies) lives in one place:** `assistant/knowledge_base.json`.
Update the founder's name, customer care numbers, WhatsApp link, pricing
note, FAQs, business hours, or policy text there — `assistant/engine.py`
never hardcodes those facts, it reads them via `assistant/kb.py`. The
file is cached in memory for the life of the process, so restart the
app (or call `kb.get_kb.cache_clear()`) after editing it. If the
assistant can't resolve a question, it now hands off to Customer Care
with a "Chat with Customer Care on WhatsApp" button built from that
same file, instead of dead-ending.

To swap the JSON file for a database table later (so staff can edit
the knowledge base from the Django admin instead of a file), replace
`kb.get_kb()` with a query returning the same dict shape — nothing in
`engine.py` needs to change.

To upgrade the assistant to a real LLM:
```bash
pip install openai
export OPENAI_API_KEY=sk-...
```
If the key is set (and the `openai` package is installed), the assistant
tries OpenAI first — using a system prompt built from the same
knowledge base file — and only falls back to the built-in rule-based
logic if that call fails for any reason, so the widget can never go
fully silent.

Staff can turn the widget on/off site-wide from `/automation/`.

## 3b. AI Hub — Image & Video generators

A new `ai_hub` app extending the assistant into a small suite of modular
AI tools, landing page at `/ai-hub/`.

**Image generator** (`/ai-hub/image/`) — works out of the box once
`OPENAI_API_KEY` is set (see `.env.example`). Built against
`ai_hub/providers.py`, which is a provider registry, not a hardcoded
OpenAI call: `AI_IMAGE_PROVIDER` picks which one is active (default
`openai`), and a second provider (`stability`) is already registered as
an example of the seam — implement its `generate()` method and set
`STABILITY_API_KEY` to bring it online, no other code changes needed.
With no key configured, the page and the API both degrade to a friendly
"not set up yet" message instead of a 500.

**Video generator** (`/ai-hub/video/`) — same pattern in
`ai_hub/video_providers.py`, supporting Runway (default) or Luma via
`AI_VIDEO_PROVIDER`, `RUNWAY_API_KEY` / `LUMA_API_KEY`. Video generation
is asynchronous on both providers (submit a prompt, poll for
completion), so the page submits a job and polls `/ai-hub/video/<id>/status/`
every few seconds until it's ready. **Caveat:** I couldn't call either
provider's live API to verify the exact current request/response shape
against real credentials — the endpoints, payload fields, and status
values in `video_providers.py` reflect each provider's documented API
as of this writing. Treat it as a solid structural starting point, but
check it against Runway's/Luma's current API reference before relying
on it in production.

Both generators log every request (success or failure) to
`GeneratedImage` / `GeneratedVideo` models, visible per-user as history
on each tool's page and in full via `/admin/ai_hub/`.

## 4. What's required for full production use

| Feature | Requirement | Works without it? |
|---|---|---|
| In-app daily notifications | Nothing extra | Yes, fully |
| Email notifications | `GENIUZLAB_EMAIL_HOST` + SMTP credentials (see `geniuzlab/settings.py`) | Yes — emails print to console in DEBUG |
| Celery-based scheduling | `CELERY_BROKER_URL` (Redis) | Yes — use `run_automation_scheduler` or cron instead |
| Real AI assistant replies | `OPENAI_API_KEY` + `pip install openai` | Yes — rule-based fallback is always active |
| Daily Bible verse | Nothing extra | Yes, fully (verse pool is local data, not an API) |
| AI Hub image generator | `OPENAI_API_KEY` (or another configured provider) | Page loads either way; generating requires the key |
| AI Hub video generator | `RUNWAY_API_KEY` or `LUMA_API_KEY` | Page loads either way; generating requires the key |

## 5. Files added/changed

- `automation/` — new app: `AutomationSettings`, `DailyMessageTemplate`,
  `NotificationLog`, `Broadcast` models; `services.py` (shared send logic);
  management commands `send_daily_notifications`,
  `run_automation_scheduler`, `seed_automation_templates`; staff dashboard
  at `/automation/`. Extended with `BibleVerse`/`BibleVerseLog` models,
  `bible_verse_enabled` setting, `run_daily_bible_verse()`,
  `send_daily_bible_verse`/`seed_bible_verses` management commands, and a
  matching Celery task/scheduler hook/dashboard controls.
- `assistant/` — new app: `AssistantLog` model, rule-based + OpenAI-ready
  `engine.py`, `/assistant/ask/` JSON endpoint.
- `ai_hub/` — new app: `GeneratedImage`/`GeneratedVideo` models,
  `providers.py`/`video_providers.py` (env-driven provider registries),
  `/ai-hub/`, `/ai-hub/image/`, `/ai-hub/video/` pages + their JSON APIs.
- `notifications/` — added `category` field + `NotificationPreference`
  model (per-user channel + category opt-outs), delete/mark-all-read
  views, `/notifications/preferences/` page. Extended with the
  `daily_bible_verse` category so it surfaces automatically on that page.
- `chat/` — sending a message now notifies the recipient.
- `konnect/` — existing notifications tagged with categories so they're
  filterable/mutable from the preferences screen.
- `templates/base.html` — floating assistant widget wired in site-wide
  (skipped only on the few templates that don't extend `base.html`, e.g.
  the raw login/register/password pages). Also added an "AI Hub" nav link.
- `geniuzlab/settings.py`, `geniuzlab/celery.py`, `geniuzlab/urls.py` —
  new apps registered, Celery app added, Celery/OpenAI settings added.

## 6. Known gaps / what to verify before launch

- Push notifications (Firebase/PWA) are **not** implemented — the spec
  asked for "readiness" only, and this build doesn't include a service
  worker or FCM wiring. Flag this if you need actual push delivery.
- The "Run Now" button on the automation dashboard runs synchronously in
  the request/response cycle. Fine for a small user base; for a large one,
  dispatch `automation.tasks.send_daily_notifications_task.delay(force=True)`
  instead once Celery is running.
- I could not run `python manage.py migrate` / `makemigrations` or start
  the dev server in this environment (no Django install, no network
  access to install it) — migrations were written by hand, matching this
  project's existing migration style exactly, and every changed `.py` file
  was syntax-checked, but you should run `python manage.py migrate` and
  click through `/automation/`, `/notifications/preferences/`, and the
  chat widget yourself before considering this "verified."
