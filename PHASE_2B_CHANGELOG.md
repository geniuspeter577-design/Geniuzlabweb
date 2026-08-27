# GeniuzLab — Phase 2B: Production-Readiness Fixes Changelog

Date: 2026-07-20
Scope: closing out the "Remaining Recommendations" from `PRE_SECURITY_STATUS.md`
(Section 5, items 1–3) ahead of shipping. This is a continuation of that
review, not a new audit — same codebase, same methodology (every line below
corresponds to an actual changed file).

Django still isn't installable in this sandbox (no network access), so as
before: `manage.py check --deploy` and `makemigrations --check --dry-run`
could not be run here. Every migration below was hand-written to match the
model change it accompanies and reviewed for consistency (field type,
`max_length`, `choices`, `default`) against the current model state — treat
`makemigrations --check --dry-run` in your own environment as the first
verification step regardless.

## Fixed

1. **`User.email` had no DB-level uniqueness constraint** (Recommendation
   #1). Application-level checks already existed in `register()` and
   `edit_profile()`, but a race between two concurrent requests could still
   produce duplicate emails — a real gap given password reset is
   email-based.
   - `accounts/models.py` — `email` field now overridden with
     `unique=True`, with a comment pointing at the dedup command below.
   - `accounts/management/commands/find_duplicate_emails.py` (new) — a
     read-only report of any accounts that already share an email, meant
     to be run *before* applying the migration on an existing database.
     Idempotent, makes no changes.
   - `accounts/migrations/0005_user_email_unique.py` (new).

2. **Missing indexes on frequently-filtered status/flag columns**
   (Recommendation #2). Each of these is queried by value (not by FK, which
   Django already indexes automatically) on hot paths — order history,
   admin filtering, the notification bell, the open-jobs list, pending
   hire/collab requests.
   - `payments/models.py` — `Transaction.status` → `db_index=True`.
     `payments/migrations/0002_transaction_status_index.py` (new).
   - `vtu/models.py` — `VTUOrder.status` → `db_index=True`.
     `vtu/migrations/0002_vtuorder_status_index.py` (new).
   - `notifications/models.py` — `Notification.is_read` → `db_index=True`.
     `notifications/migrations/0005_notification_is_read_index.py` (new).
   - `konnect/models.py` — `ServiceRequest.status`, `Job.status`,
     `CollaborationRequest.status` → `db_index=True`.
     `konnect/migrations/0006_status_indexes.py` (new).

3. **No idempotency/double-submit guard on financial forms**
   (Recommendation #3). A double-click or resubmitted request previously
   just created two separate, correctly wallet-balanced transactions rather
   than being rejected — not a fraud risk (row-locked, idempotent per
   request) but unnecessary support load. Client-side disable-on-submit
   already existed on the auth forms (login/register); this extends the
   same pattern to the money-moving forms instead of duplicating an inline
   script six times.
   - `static/js/prevent-double-submit.js` (new) — disables a form's submit
     button the instant it's submitted, for any form marked
     `data-guard-submit`. No effect on forms that don't opt in.
   - `templates/base.html` — includes the new script sitewide.
   - `templates/pages/subs.html`, `templates/vtu/airtime.html`,
     `templates/vtu/data.html`, `templates/vtu/cable.html`,
     `templates/vtu/electricity.html`, `templates/vtu/education.html` —
     added the `data-guard-submit` attribute to each purchase/subscribe
     form.

## Not changed (still open, non-blocking)

- **Email verification** (Recommendation #4) — registration/email changes
  still take effect immediately with no confirmation link. Not a
  vulnerability given Django's per-user password-reset tokens, but a real
  feature addition (new model/token flow/templates), out of scope for a
  hardening pass. Flagged again here so it isn't lost.
- **`chat.start_conversation` / `notifications.mark_read`** remain
  GET-triggered by design (Recommendation #5) — idempotent, non-destructive,
  intentionally left as-is.
- **Centralizing public contact details** (Recommendation #6) — cosmetic
  maintainability item only, not touched.

## Runtime checklist addition

Before deploying this round's changes on top of an existing (non-empty)
database:

- [ ] Run `python manage.py find_duplicate_emails` — resolve any reported
      duplicates before migrating.
- [ ] Run `python manage.py makemigrations --check --dry-run` to confirm no
      drift (could not be run in this sandbox).
- [ ] Run `python manage.py migrate`.
