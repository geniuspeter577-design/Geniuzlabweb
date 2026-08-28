# GeniuzLab Engineering Audit

**Audit date:** 2026-08-28  
**Scope:** project structure, application logic, feature completeness, security posture, runtime readiness, test coverage, deployment operations, and documentation.  
**Repository:** `Geniuzlabweb`, branch `main`

## Executive assessment

GeniuzLab is a substantial Django 5 monolith containing authentication, marketplace, academy/LMS, subscriptions, wallet, payment foundations, VTU, chat, notifications, automation, assistant, and AI generation features. The architecture is understandable and the code has strong foundations: environment-based secrets, a custom user model, ownership-filtered queries, upload validators, row-locked wallet debits, feature flags, and provider abstractions.

**Readiness decision: NOT READY for production money movement or general release.** Local application tests pass, but the repository currently has migration drift, no implemented payment gateway lifecycle, no committed environment template or deployment contract, and incomplete operational verification. It is suitable for continued development and controlled local or staging testing.

## Verified evidence

| Check | Result | Meaning |
|---|---|---|
| `python -m compileall -q .` | Pass | Python source compiles. |
| `GENIUZLAB_DEBUG=True python manage.py test --noinput` | Pass: 52 tests | Existing automated tests are green; coverage is concentrated in `academy` and `ai_hub`. |
| `python manage.py collectstatic --noinput` | Pass: 150 copied, 426 processed | WhiteNoise asset collection works when explicitly run. |
| `python manage.py check --deploy` | Blocked in production mode; local debug reports expected warnings | Fail-closed settings require production secrets and hosts. A real production env still needs a clean deploy check. |
| `python manage.py makemigrations --check --dry-run` | Pass after generating five migrations | Model and migration state is now synchronized in the working tree. |
| `smoke_test.py` with `testserver` allowed and no migrated schema | Fail: 17 checks | Remaining failures were missing database tables and disabled/no-key paths, not host rejection. |

The smoke test initially returned 37 HTTP 400 failures because Django's test client host, `testserver`, was not in `ALLOWED_HOSTS`. With that host allowed, public static-backed pages passed, while database-backed journeys revealed the empty/stale local schema. This distinction should be preserved in future CI setup.

## Findings

### P0 release blockers

1. **Migration release process.** The five generated migrations now clear the local drift check and apply successfully to a fresh local database. They still need review, commit, and application to a staging copy before deployment.

2. **Payments are not an integration.** `payments/views.py` creates a pending `Transaction` and redirects to a receipt. It does not initiate hosted checkout, verify callbacks, authenticate webhooks, or call `Transaction.mark_success()` from a provider event. `mark_success()` only changes transaction status; it does not credit the wallet. Treat the payment app as a ledger/UI foundation, not a usable payment system.

3. **Database bootstrap is not represented by the checked-in database.** The smoke test against the current `db.sqlite3` found missing tables. Fresh environments must run migrations, and production must use the configured Postgres-compatible `GENIUZLAB_DATABASE_URL` rather than SQLite.

### P1 high priority

4. **No complete environment/deployment contract is committed.** README and automation docs reference `.env.example`, but that file is absent. A basic CI workflow now exists, but there is still no container manifest, process definition, health endpoint, or documented backup/restore procedure.

5. **Money operations need idempotency.** Wallet debit locking prevents a negative balance under concurrency, but repeated requests can still create multiple valid subscription or VTU orders. Add server-side idempotency keys and durable provider request IDs before enabling these features.

6. **VTU reconciliation is request-bound.** Purchases debit the wallet before the provider call and refund on immediate failure. Pending orders depend on later requery; there is no worker-driven reconciliation, timeout policy, audit event model, or provider webhook path. The feature is disabled by default, which is appropriate until this is hardened.

7. **Runtime smoke coverage is environment-sensitive.** The script assumes migrated tables and does not automatically set `ALLOWED_HOSTS` or run migrations. Make this explicit in CI or create a dedicated test command that provisions an isolated database first.

### P2 important follow-up

8. **Test coverage is uneven.** There are 52 passing tests, but most app test modules are empty stubs. Marketplace authorization, wallet invariants, payments, VTU reconciliation, automation duplication, uploads, and production settings need focused tests.

9. **Automation has scaling limits.** The admin "Run Now" path performs work synchronously, and notification email failures use `fail_silently=True`. Prefer Celery dispatch for large audiences and record delivery outcomes.

10. **Synchronous AI streaming limits concurrency.** AI chat holds a Django worker while a `requests` stream is open. This is acceptable for modest traffic but should move to an async-capable or job-backed design as usage grows.

11. **Email verification is absent.** Registration and email edits become active immediately. Add verification before treating email as a trusted identity or notification channel.

## Restructuring progress

The Django project package has been extracted to `backend/geniuzlab`, with
working `backend/manage.py`, `backend/wsgi.py`, and `backend/asgi.py` entry
points. Root `geniuzlab.*` wrappers preserve legacy commands and historical
migration imports. All 13 first-party Django apps have now been extracted to
`apps/` with their original Django labels preserved for database compatibility.
Templates and static assets remain at the root for a later individually tested
extraction.

The migrated application structure passed the HTTP smoke test: all journeys
passed, including the expected 404 for the disabled subscription feature.

## Architecture and feature inventory

The root URL configuration exposes 13 first-party apps. `accounts` owns the custom user and auth flows; `dashboard` composes role-specific views; `konnect` owns marketplace/social behavior; `academy` owns courses and enrollment; `wallet` and `payments` own financial records; `vtu` integrates VTpass; `chat`, `notifications`, and `automation` provide communication; `assistant` and `ai_hub` provide rule-based/LLM and generation features.

The design is a conventional server-rendered Django application with progressive JSON/SSE endpoints. Celery/Redis are optional infrastructure for automation, while SQLite is intended only for local debug mode.

## Strengths to preserve

- Production settings fail closed when secret key, hosts, database, CSRF origins, or email transport are missing.
- Authenticated object queries generally include the current user, reducing IDOR risk.
- Upload validation centralizes extension, content type, size, and image-byte checks.
- Wallet debits use `select_for_update()` inside transactions.
- AI integrations use provider seams and degrade gracefully when keys are absent.
- Feature flags hide unfinished VTU/wallet surfaces without deleting schema.

## Recommended delivery sequence

1. Generate, review, and commit migrations; migrate a staging database; remove stale local database assumptions.
2. Add `.env.example`, CI checks, `check --deploy`, migration checks, collectstatic, tests, and a database-backed smoke job.
3. Implement one payment provider completely: checkout, signed callback or webhook, idempotent transaction transition, wallet credit, replay tests, and reconciliation tooling.
4. Add wallet/subscription/VTU idempotency and background reconciliation.
5. Expand authorization and financial tests, then run staging load and provider sandbox tests.
6. Only then enable VTU and real payment feature flags in production.

## Audit conclusion

The codebase has a credible product foundation and is farther along than a prototype, but "implemented UI and models" currently exceeds "operationally verified service." The next work should be release engineering and financial correctness, not another broad feature expansion.
