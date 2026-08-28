# Testing Guide

## Current baseline

The verified local baseline on 2026-08-28 is:

- 52 Django tests pass after static collection.
- Python compilation passes.
- Static collection processes 426 assets.
- Migration drift check passes after the five pending migrations were generated.
- The smoke test requires migrated tables and `testserver` in `GENIUZLAB_ALLOWED_HOSTS`.

## Commands

```bash
GENIUZLAB_DEBUG=True python manage.py test --noinput
GENIUZLAB_DEBUG=True python manage.py makemigrations --check --dry-run
GENIUZLAB_DEBUG=True python manage.py collectstatic --noinput
GENIUZLAB_DEBUG=True GENIUZLAB_ALLOWED_HOSTS='testserver,localhost,127.0.0.1' python smoke_test.py
```

Run `migrate` before the smoke test when using the repository database. CI should use a disposable database and provision migrations as part of the job.

## Coverage priorities

Add tests for wallet concurrency and ledger invariants, payment callback signature/replay/idempotency behavior, VTU refund/requery transitions, subscription duplicate submission, authorization across every marketplace object, upload validators, automation duplicate delivery, and production settings failures. The currently passing suite is useful but does not prove those high-risk contracts.
