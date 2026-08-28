# GeniuzLab — Creative Technology Ecosystem

## What this project now contains

## Current status

This is a feature-rich Django monolith with working local flows, but it is
not production-ready yet. The highest-priority release blockers are:

- migration consistency is now clean after generating the five pending
  migrations for `academy`, `automation`, `konnect`, `motion`, and
  `notifications`;
- payment checkout/webhooks are not implemented, so no real gateway charge or
  verified wallet credit occurs; and
- deployment still needs a real environment, database, static collection,
  email transport, and provider smoke tests.

The detailed audit and working project documentation live in
[`audit_result.md`](audit_result.md) and [`DOCs/`](DOCs/README.md).

The restructuring foundations are staged in [`backend/`](backend/README.md),
[`apps/`](apps/README.md), [`frontend/`](frontend/README.md),
[`mobile/`](mobile/README.md), and [`infra/`](infra/README.md). Templates and
static files remain at the root until their ownership is extracted.
`backend.geniuzlab` and `apps.*` are now the canonical project and application
packages; root `geniuzlab.*` modules are compatibility wrappers.

- **accounts** — custom User model (roles: customer/creative/student/instructor/admin), register, login, logout, profile, edit profile
- **konnect** — the marketplace: creative profiles + portfolios, hire-a-creative browsing, service requests, job posting/browsing/applications, collaboration requests
- **academy** — Geniuz Academy hub at `/academy/` linking the 4 existing course pages
- **motion** — GENIUZinMOTION brand page at `/motion/`
- **subs** — GeniuzSubs subscription plans + wallet-based subscribing at `/subs/`
- **graphics** — Geniuz Graphics brand page at `/graphics/` (served from `dashboard`)
- **payments** — Transaction model + foundation for Paystack / Flutterwave / Monnify (see below)
- **wallet** — internal wallet balance + ledger, used by subs and payments
- **chat** — direct messaging between users (backs "Collaborate → communicate")
- **notifications** — in-app notifications, surfaced in the navbar bell
- **ai_hub** — AI Chat (OpenAI, streaming, per-conversation memory, Markdown/code rendering), AI Image Generator (OpenAI Images, pluggable provider seam), AI Video Generator (Runway/Luma, pluggable provider seam, async job polling)
- **assistant** — the corner chat-widget site assistant: rule-based site navigation/FAQ first, with an OpenAI fallback for open-ended questions (separate from the full-page AI Hub Chat)
- **automation** — Daily Bible Verse (bible-api.com, no key required) + other scheduled/notification jobs, see `README_AUTOMATION.md`
- **Light/Dark mode** — sitewide toggle (navbar, desktop + mobile), persisted in `localStorage`, applied before first paint to avoid a flash of the wrong theme; built on the existing `--gl-*` CSS custom-property design system in `static/css/style.css`

## Running locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create a local .env, or export the values in your shell.
export GENIUZLAB_DEBUG=True
export GENIUZLAB_SECRET_KEY=local-development-only

python backend/manage.py migrate
python backend/manage.py createsuperuser
python backend/manage.py seed_showcase_content   # optional — populates portfolio/motion showcase demo entries
python backend/manage.py collectstatic --noinput
python backend/manage.py runserver
```

There is currently no committed `.env.example`; use
[`DOCs/OPERATIONS.md`](DOCs/OPERATIONS.md) as the environment checklist.

Then visit `http://127.0.0.1:8000/`.

> The committed local `db.sqlite3` may be empty or stale. Treat migrations as
> the source of truth and run `python manage.py migrate` before testing pages.

> `seed_showcase_content` creates one demo "GeniuzLab Studio" creative
> profile with a few example portfolio/motion entries, using the
> procedurally generated brand imagery in `static/images/generated/` — no
> personal photos involved. It's idempotent and purely cosmetic (makes the
> showcase pages look populated instead of empty on a fresh install); safe
> to skip, and safe to re-run.

## Payments — connecting real gateways

Payments currently provide transaction records, receipts, and admin-facing
status scaffolding. They do not yet perform a real checkout or verified wallet
credit, even with provider keys configured — new transactions are recorded as
`pending` until a provider lifecycle is implemented.

To go live with a provider, set its keys in `.env` (see `.env.example`),
then implement the actual checkout call in
`payments/views.py::initiate_payment` (redirect to the provider's hosted
checkout, or call their charge API) and add a webhook/callback view that
authenticates the event, transitions the transaction idempotently, and credits
the wallet only after verified success. The `Transaction` model, admin,
history page and receipt page are foundations, not a complete integration.

## AI Hub — Chat, Image, Video

All three AI Hub tools read credentials from environment variables only
(see `.env.example`) and never hardcode a key. Each shows a friendly
"not set up yet" message — never a 500 — when its key is missing:

- **Chat** (`ai_hub/chat_provider.py`) — `OPENAI_API_KEY` (+ optional
  `OPENAI_CHAT_MODEL`, default `gpt-4o-mini`). Streams replies via
  Server-Sent Events; each conversation's full message history is
  replayed to the API on every turn for real multi-turn memory.
- **Image** (`ai_hub/providers.py`) — same `OPENAI_API_KEY`.
- **Video** (`ai_hub/video_providers.py`) — `RUNWAY_API_KEY` and/or
  `LUMA_API_KEY`, switchable via `AI_VIDEO_PROVIDER`.

There is intentionally only **one** `OPENAI_API_KEY` for the whole
project — chat, images, and any future OpenAI feature all read it.

## Known limitations / what's still open

- Verified 2026-08-28: all 52 Django tests pass after `collectstatic`,
  and `makemigrations --check --dry-run` now reports no changes after the
  generated migrations were applied locally. Review them in staging before
  deployment.
- Payment gateway checkout calls are stubbed (see above) — no live charge
  is made yet.
- Chat (direct messaging, the `chat` app) is simple request/response
  messaging (no WebSockets/live updates). AI Hub Chat streams via
  Server-Sent Events, which is separate from this.
- Automated tests exist, but coverage is concentrated in `academy` and
  `ai_hub`; most app test modules remain empty stubs.
- Image uploads (avatars, portfolio images) need `Pillow` (already in
  `requirements.txt`) and `MEDIA_ROOT` served in production via your web
  server or a storage backend (S3, etc.) — currently only auto-served
  in `DEBUG` mode.
- Light/Dark mode covers the sitewide design-token surfaces (backgrounds,
  text, borders, cards, forms) across every template, since they all
  extend `base.html` and inherit `style.css`. A small number of
  inline `style="color:#..."` attributes inside individual templates
  (rather than in the stylesheets) were not swept — cosmetic, low-risk,
  worth a follow-up pass if you spot one.
- AI Hub Chat streaming runs on a synchronous Django view
  (`StreamingHttpResponse` over a `requests` streaming call) — fine at
  moderate traffic, but a high-concurrency production deployment would
  benefit from an ASGI/async view or a task-queue-backed approach later.
- VTU is feature-flagged off by default. Wallet/subscription/VTU flows need
  server-side idempotency and background reconciliation before real money
  movement is enabled.
- There is no committed `.env.example`, CI pipeline, deployment manifest,
  health check, structured production logging policy, or backup/restore
  runbook yet.
