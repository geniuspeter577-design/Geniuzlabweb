# Readiness Roadmap

## Restructuring principles

- Preserve runtime behavior and public URL contracts at every step.
- Make one ownership move per change, with tests and deployment commands
	updated in the same change.
- Keep compatibility wrappers until the relocated packages have passed
	management, migration, smoke, and staging verification.
- Define API contracts before introducing separate web or mobile clients.

## Structure sequence

1. Add repository foundations and ownership documentation.
2. Add CI and operational assets under `infra/`.
3. Adopt the `backend/` management, WSGI, and ASGI compatibility entry points.
4. Extract the Django project package into `backend/` with compatibility shims. (Complete.)
5. Extract Django product apps into `apps/` one at a time. (Complete.)
6. Extract templates and static assets only after discovery paths and tests are
	updated. (Next.)
7. Extract browser UI into `frontend/` only after API boundaries are tested.
8. Build mobile clients in `mobile/` against versioned APIs.

## Gate 1: repository correctness

- Review and commit the generated migrations in the five affected apps, then
	apply them to staging. (Local generation and application complete.)
- Remove stale claims that migration history is clean.
- Add the missing environment template or make the setup docs authoritative.
- Add CI for checks, migrations, tests, and static collection.

## Gate 2: financial correctness

- Complete one gateway integration end to end.
- Verify signed callbacks/webhooks and make state transitions idempotent.
- Credit wallets only from verified successful events.
- Add idempotency keys, audit events, and reconciliation reports.

## Gate 3: operational reliability

- Move notification broadcasts and provider reconciliation to workers.
- Add health/readiness checks, structured logs, alerting, and backup restore drills.
- Configure durable media storage and email delivery.

## Gate 4: release validation

- Run marketplace, academy, auth, wallet, VTU, and provider sandbox journeys on staging.
- Test rollback and migration recovery.
- Review security headers and `check --deploy` with real production values.
- Enable feature flags incrementally and monitor financial reconciliation.
