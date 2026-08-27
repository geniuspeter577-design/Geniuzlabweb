# GeniuzLab — Pre-Security (Phase 2) Engineering Status

Date of review: 2026-07-19
Scope: full codebase review of `geniuzlab_web_project_audited.zip` prior to starting
Phase 2 (Production Security).

---

## 1. Architecture Summary

Django 5.x monolith, 13 first-party apps sharing one Postgres/SQLite database,
served by gunicorn + whitenoise, with Celery/Redis for background jobs.

| App | Purpose |
|---|---|
| `accounts` | Custom `User` model, auth, profiles, presence |
| `academy` | Courses, enrollments, assignments, certificates |
| `konnect` | Creative marketplace: portfolios, feed, jobs, hiring, social graph |
| `motion` | Public motion-graphics showcase |
| `subs` | GeniuzLab Premium subscription plans |
| `wallet` | Internal NGN wallet ledger (credit/debit, row-locked) |
| `payments` | External gateway transactions (Paystack/Flutterwave/Monnify) |
| `vtu` | Airtime/data/cable/electricity/exam-pin purchases via VTpass |
| `chat` | Direct messaging with attachments |
| `notifications` | In-app notifications + preferences |
| `automation` | Daily notification engine + admin broadcast tool |
| `assistant` | Rule-based/optional-LLM chat widget, JSON knowledge base |
| `dashboard` | Role-aware dashboard aggregating the above |

Settings (`geniuzlab/settings.py`) are environment-driven with hard failures
if production-required variables are missing (secret key, allowed hosts,
database URL, CSRF trusted origins, email transport). This is a strong,
already-in-place pattern — production cannot silently boot in an insecure
state.

---

## 2. Apps Audited

All 13 apps: models, views, forms, uploads, migrations, and templates were
reviewed. `konnect`, `vtu`, `accounts`, and `automation` (the highest-risk /
highest-traffic surfaces — money, auth, uploads) got the deepest pass.

---

## 3. Bugs Found & Fixed This Session

All fixes below were applied directly to the codebase during this review.

| # | Issue | File(s) | Severity | Fix |
|---|---|---|---|---|
| 1 | `subs.subscribe` debited the wallet and created a subscription with **no `@require_POST`/method check** — reachable via a bare GET request, which Django's CSRF middleware does not protect (it only checks unsafe methods). A crafted link or `<img>` tag could have charged a logged-in victim's wallet. | `subs/views.py` | **Critical** | Added `@require_POST`. |
| 2 | `konnect.respond_service_request` (accept/decline a hire request) had no method check. | `konnect/views.py` | High | Added `@require_POST`. |
| 3 | `konnect.respond_collaboration_request` had no method check **and** was wired to a plain `<a href>` GET link in the template — this one was actually exploitable as shipped. | `konnect/views.py`, `templates/pages/collaborate.html` | High | Added `@require_POST`; converted the Accept/Decline links to CSRF-protected POST forms. |
| 4 | `konnect.send_collaboration_request` had no method check. | `konnect/views.py` | Medium | Added `@require_POST`. |
| 5 | `konnect.toggle_saved_creative` had no method check (both call sites already used POST forms, so this is defense-in-depth). | `konnect/views.py` | Low | Added `@require_POST`. |
| 6 | `academy.enroll_course` had no method check (already always POSTed from the template; low-impact even if forced — enrolling in a free course). | `academy/views.py` | Low | Added `@require_POST`. |
| 7 | `accounts.edit_profile` let a user change their email to **any address already in use by another account** — no uniqueness check (only `register` had one). Combined with `User.email` having no DB-level `unique` constraint, this is a real gap given that password reset is email-based. | `accounts/views.py` | Medium | Added the same duplicate-email check `register` already does. |

**Not changed, flagged as accepted low risk / recommendation instead of a fix:**
- `chat.start_conversation` and `notifications.mark_read` are intentionally
  GET-triggered navigation links with idempotent, non-destructive side effects
  (get-or-create a conversation; mark one notification read). Forcing these to
  POST would require a UX rework for negligible security benefit — left as-is,
  called out below under Recommendations.

---

## 4. Verification Detail

### Models
- Every FK has an explicit, deliberate `on_delete` (`CASCADE` for
  owned/dependent rows, `SET_NULL` for optional references like
  `Broadcast.created_by`, `Message.reply_to`, `ServiceRequest.conversation`).
- Uniqueness is enforced where it matters: `unique_together` on
  `ProjectLike`, `SavedProject`, `Follow`, `JobApplication`,
  `CollaborationRequest`, `SavedCreative`, `Enrollment`,
  `AssignmentSubmission`, `Certificate`, `NotificationLog`; `OneToOneField`
  for `CreativeProfile`/`CustomerProfile`/`Wallet`/`NotificationPreference`.
- One real gap: **`User.email` has no `unique=True`** (inherited from
  `AbstractUser`, never overridden), and `register()`'s uniqueness check is a
  check-then-create with no DB constraint backing it, so a race between two
  concurrent registrations could still produce duplicate emails. See
  Recommendations — needs a data-dedup pass before a migration can safely add
  the constraint, so it wasn't done in this session.
- No missing indexes causing correctness bugs, but see Recommendations for
  performance-oriented indexes worth adding as data grows.
- `select_related`/`prefetch_related` are already used deliberately and
  correctly throughout the hot paths (`konnect` feed/discover/search,
  `dashboard`, `chat.Conversation.other_participant`/`last_message`), including
  query-count comments explaining *why*. No N+1 issues found in the templates
  checked.

### Forms
- Django's `forms.Form` is only used in `vtu/forms.py` (fully validated:
  `DecimalField(min_value=...)`, `ChoiceField`, `IntegerField(min_value=1,
  max_value=10)`). Every other app validates directly in the view from
  `request.POST` with explicit type coercion (`Decimal(...)` wrapped in
  `try/except (InvalidOperation, TypeError)`, integer clamping with
  `max(0, min(23, ...))`, etc.) — consistent and safe, if less DRY than
  `ModelForm`s would be.
- Duplicate-submission protection: login/register/password-reset templates
  already disable the submit button on click. Financial actions
  (`vtu.buy_*`, `subs.subscribe`) don't have client-side double-submit
  guards — low risk today since the wallet debit is row-locked and
  idempotent per request, but see Recommendations.

### Uploads
`geniuzlab/validators.py` is the single shared validation path for every
`ImageField`/`FileField` in the project:
- Extension allowlist per upload type (images / chat documents & source
  files / video).
- Declared `content_type` cross-checked against an allowlist.
- Size limits per type, all overridable via env var
  (`GENIUZLAB_MAX_CHAT_ATTACHMENT_SIZE`, `GENIUZLAB_MAX_VIDEO_UPLOAD_SIZE`).
- Images are opened and `.verify()`'d with Pillow — blocks a renamed
  script/executable disguised with an image extension.
- Path traversal / filename sanitization: handled by Django's default
  `FileSystemStorage.get_valid_name()` (strips `..`, path separators, and
  unsafe characters); nothing in the project overrides or bypasses this.

### API endpoints / POST requests
- **CSRF:** zero `@csrf_exempt` views and no webhook endpoints anywhere in
  the project; every `<form method="post">` in every template carries
  `{% csrf_token %}` (verified across all templates, not spot-checked).
- **Auth:** `@login_required` is applied consistently on every
  account-scoped view; `@staff_member_required` gates the entire
  `automation` admin surface.
- **Authorization:** every object-scoped view fetches with the owner baked
  into the query (`get_object_or_404(Model, pk=pk, user=request.user)` or
  equivalent — e.g. `creative__user=request.user`,
  `participants=request.user`), so there are no IDOR paths found where one
  user could load or mutate another's row by guessing a primary key.
- **Method enforcement:** this was the main gap category — see Section 3.
  Fixed the ones with real impact (money, hire/collab state).
- Rate limiting: `accounts.register` and `accounts.user_login` are
  rate-limited via `django-ratelimit` (by IP and, for login, additionally by
  submitted username) — good protection against credential stuffing /
  registration spam.
- Open redirect: `user_login`'s `next` param is validated with
  `url_has_allowed_host_and_scheme` before redirecting — correct.

### TODO / FIXME / debug code
No `TODO`, `FIXME`, debug `print()`, or placeholder `pass` statements found
in any application code. The only `print()` calls are in the standalone
`smoke_test.py` CLI script (expected/correct there). The two bare `pass`
statements found (`chat/views.py`, `accounts/middleware.py`) are intentional,
narrow `except: pass` guards with explanatory comments, not placeholders.

### Hardcoded secrets / contact info
- No API keys, passwords, or secrets hardcoded anywhere — every credential
  (`GENIUZLAB_SECRET_KEY`, all payment provider keys, `VTPASS_*`,
  `OPENAI_API_KEY`, email credentials) is already read from the environment
  in `settings.py`, with the dev-only fallback secret key gated behind
  `DEBUG`.
- Found business contact details hardcoded in templates and the assistant's
  JSON knowledge base: a support email (`templates/base.html`,
  `templates/partials/contact_button.html`) and a WhatsApp
  number/call numbers (`assistant/knowledge_base.json`). **These are public
  business content, not secrets** — they're meant to be shown to every
  visitor, and the knowledge base is already externalized to JSON
  specifically so staff can update it without touching code. Moving these
  into environment variables wouldn't add security value (env vars are for
  per-environment/sensitive config, not public marketing content) — left
  as-is. Flagged as a recommendation only if the business wants single-place
  editing without a deploy.

### Migrations
Every app's migration history is a clean linear chain — no duplicate numbers,
no branches, no missing dependencies. Cross-app dependencies are correct
where they exist (e.g. `konnect.0005_servicerequest_conversation` correctly
depends on `chat.0002_message_attachment_reply` for the new FK). Django itself
wasn't available in this sandbox (no network access to install it), so
`makemigrations --check --dry-run` could not be run automatically — do this
as the first step of your own environment before Phase 2 (see Runtime
Checklist).

---

## 5. Remaining Recommendations (non-blocking)

1. **Add a DB-level `unique=True` on `User.email`.** Needs a one-time
   dedup pass against production data first (find & resolve any existing
   duplicate emails), then a migration. Until then, rely on the
   application-level checks (now present in both `register` and
   `edit_profile`).
2. **Add explicit indexes** as data volume grows, on the fields queried by
   status/flag rather than by FK (which are already indexed automatically):
   `Transaction.status`, `VTUOrder.status`, `Notification.is_read`,
   `ServiceRequest.status`, `Job.status`. Not urgent at current scale.
3. **Idempotency key for `_process_purchase` and `subscribe`.** A
   double-click or resubmitted request currently just creates two separate
   (correctly wallet-balanced) transactions rather than being rejected —
   not a fraud risk, but a UX/support-load one. A client-side
   disable-on-submit (already used on the auth forms) or a short-lived
   server-side idempotency token would close this.
4. **Email verification.** Registration and email changes take effect
   immediately with no confirmation link. Not a vulnerability given
   Django's per-user password-reset tokens, but worth having before
   relying on email for anything more sensitive than notifications.
5. **`chat.start_conversation` / `notifications.mark_read`** remain
   GET-triggered by design (see Section 3) — acceptable, but note it if a
   future audit tightens method enforcement project-wide.
6. Consider centralizing the public contact details (support email,
   WhatsApp number) referenced in Section 4 into `settings.py` /
   `AutomationSettings` so they're editable from one place — purely a
   maintainability nicety, not a security item.

---

## 6. Environment Variable Checklist

Required in production (app raises `RuntimeError` at boot if missing):

- [ ] `GENIUZLAB_SECRET_KEY`
- [ ] `GENIUZLAB_ALLOWED_HOSTS`
- [ ] `GENIUZLAB_DATABASE_URL`
- [ ] `GENIUZLAB_CSRF_TRUSTED_ORIGINS`
- [ ] `GENIUZLAB_EMAIL_HOST` (+ `GENIUZLAB_EMAIL_HOST_USER` /
      `GENIUZLAB_EMAIL_HOST_PASSWORD`, or emails silently go to console)

Recommended / feature-gating (safe defaults if unset):

- [ ] `GENIUZLAB_DEBUG` (must be unset or `False` in production)
- [ ] `GENIUZLAB_SECURE_SSL_REDIRECT`
- [ ] `GENIUZLAB_EMAIL_PORT`, `GENIUZLAB_EMAIL_USE_SSL` / `_USE_TLS`,
      `GENIUZLAB_EMAIL_TIMEOUT`
- [ ] `GENIUZLAB_DEFAULT_FROM_EMAIL`, `GENIUZLAB_SERVER_EMAIL`
- [ ] `GENIUZLAB_REDIS_CACHE_URL`
- [ ] `GENIUZLAB_MAX_CHAT_ATTACHMENT_SIZE`, `GENIUZLAB_MAX_VIDEO_UPLOAD_SIZE`
- [ ] `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- [ ] `PAYSTACK_PUBLIC_KEY`, `PAYSTACK_SECRET_KEY`
- [ ] `FLUTTERWAVE_PUBLIC_KEY`, `FLUTTERWAVE_SECRET_KEY`
- [ ] `MONNIFY_API_KEY`, `MONNIFY_SECRET_KEY`, `MONNIFY_CONTRACT_CODE`
- [ ] `VTPASS_API_KEY`, `VTPASS_SECRET_KEY`, `VTPASS_PUBLIC_KEY`,
      `VTPASS_LIVE_MODE`
- [ ] `OPENAI_API_KEY` (optional — assistant runs rule-based without it)

---

## 7. Runtime Checklist

- [ ] Install Django + `requirements.txt` in a real environment and run
      `python manage.py check --deploy`.
- [ ] Run `python manage.py makemigrations --check --dry-run` to confirm no
      model/migration drift (could not be run in this sandbox — no network
      access to install Django).
- [ ] Run `python manage.py migrate` against a Postgres instance (not
      sqlite) before going live.
- [ ] Confirm `python manage.py collectstatic` succeeds with
      `WhiteNoiseMiddleware` in place.
- [ ] Set all required env vars from Section 6 and confirm the app boots
      with `GENIUZLAB_DEBUG` unset/`False`.
- [ ] Verify outbound email actually sends (the project already has a
      system check — `geniuzlab.E001` — that fails loudly if it can't).
- [ ] Confirm Celery worker + beat (or the `run_automation_scheduler`
      management command / cron fallback) are running for daily
      notifications.
- [ ] Smoke-test the three payment provider integrations and the VTpass
      integration against sandbox credentials before flipping
      `VTPASS_LIVE_MODE`.

## 8. Browser QA Checklist

- [ ] Register → login → logout → password reset (full email round trip)
- [ ] Edit profile: avatar/cover upload, oversized file rejected, wrong
      file type rejected, email-already-in-use rejected (newly fixed)
- [ ] Konnect: create/edit/delete a portfolio item with gallery media;
      like/comment/share/save/report a project; follow/unfollow
- [ ] Hire flow: request a service → creative accepts/declines (confirm
      the fixed POST-only endpoints still work from the UI)
- [ ] Collaboration: send a request → recipient accepts/declines from the
      new POST form (confirm the template change renders/behaves
      identically to the old link)
- [ ] Wallet: fund via `initiate_payment`, confirm pending-transaction
      messaging when no provider keys are configured
- [ ] VTU: airtime/data/cable/electricity/education purchase with
      insufficient balance, with a simulated provider failure (refund
      path), and a successful purchase
- [ ] Subscriptions: subscribe to a plan (confirm the fixed POST-only
      endpoint), insufficient-balance path
- [ ] Chat: send text + attachment (image, doc, oversized/blocked type),
      reply-to, typing indicator, unread badge
- [ ] Notifications: mark one read, mark all read, delete, preferences
      toggle
- [ ] Automation dashboard: staff-only access enforced for a non-staff
      login attempt (should redirect/deny)
- [ ] Assistant widget: anonymous + logged-in chat, customer-care
      escalation path

---

## 9. Ready for Phase 2 (Production Security)?

### **Yes**, with the fixes in this document already applied.

Reasoning:
- The codebase was already in strong shape going into this review —
  environment-driven config with hard production guardrails, no debug code,
  no hardcoded secrets, consistent CSRF/auth/authorization, real upload
  validation, and deliberate query optimization.
- The issues this review found were narrow and specific (missing
  `@require_POST` on a handful of state-changing views, one of which —
  `subs.subscribe` — was genuinely exploitable, plus one authorization gap
  in email-uniqueness) rather than systemic. All of them have been fixed in
  this session.
- Nothing outstanding (Section 5) blocks moving into Phase 2 — they're
  scaling/UX/data-hygiene improvements, not open vulnerabilities.
- The one caveat: automated `makemigrations --check` and `manage.py check
  --deploy` could not be run in this sandbox (no Django installed, no
  network access). Run both as the literal first step in Phase 2, before
  anything else, to confirm this review's manual migration analysis holds
  in your real environment.
