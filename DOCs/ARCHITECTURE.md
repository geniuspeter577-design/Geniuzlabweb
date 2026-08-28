# Architecture

## Runtime shape

GeniuzLab is a Django 5 monolith using server-rendered templates, a shared relational database, WhiteNoise for static assets, and optional Celery/Redis for scheduled work. `geniuzlab/settings.py` is environment-driven and refuses to boot production mode without core configuration.

## Restructuring target

The repository is being reorganized as a compatibility-preserving monorepo:

```text
backend/       Django runtime and server-owned concerns
apps/          Product applications and shared client packages
frontend/      Dedicated browser client, when extracted from templates
mobile/        Native or cross-platform mobile clients
infra/         CI, deployment, observability, and operational assets
DOCs/          Architecture, operations, testing, and delivery records
```

The Django project package has now moved to `backend/geniuzlab`. Root
`geniuzlab.*` modules remain compatibility wrappers for old deployment commands
and historical migration imports. All first-party Django apps now live under
`apps/` and retain their original Django labels. Templates and static files
remain at the root until their discovery paths are migrated.

### Extraction sequence

1. Establish CI and a clean migration baseline.
2. Move Django project configuration into `backend/` behind a compatibility
	entry point, then verify management, WSGI, ASGI, Celery, and test commands.
3. Move product Django apps one at a time into `apps/`, updating app labels,
	URL includes, admin imports, migration dependencies, and tests together.
4. Define versioned API contracts before extracting browser UI into
	`frontend/`.
5. Start `mobile/` only against those API contracts.
6. Add deployable assets to `infra/` after runtime paths are stable.

## App ownership

| App | Responsibility |
|---|---|
| `accounts` | Custom user, roles, authentication, profiles, presence |
| `dashboard` | Role-aware aggregation and public pages |
| `konnect` | Creative marketplace, projects, jobs, follows, collaboration |
| `academy` | Courses, modules, assignments, quizzes, enrollment payments |
| `motion` | Motion showcase |
| `subs` | Wallet-funded subscription plans |
| `wallet` | Balance and credit/debit ledger |
| `payments` | External transaction records and receipt UI; gateway work remains |
| `vtu` | VTpass catalog, purchase, order history, requery |
| `chat` | Direct user conversations and attachments |
| `notifications` | In-app notifications and preferences |
| `automation` | Daily messages, broadcasts, Bible verse, scheduler entry points |
| `assistant` | Site FAQ/rule engine with optional OpenAI fallback |
| `ai_hub` | AI chat, image generation, and video-provider adapters |

## Important flows

- Authenticated views use Django sessions and `login_required`; object lookups generally scope by the current user.
- Forms are a mix of Django forms and explicit view validation.
- Financial state is recorded in database models. Wallet mutations are transaction-wrapped and row-locked.
- Notification automation can be launched through Celery Beat, the built-in scheduler, or cron. All routes call shared service functions.
- AI chat uses SSE from a synchronous Django view; images and video are provider API calls, with video jobs polled asynchronously by the browser.

## Boundaries and risks

`payments` currently stops at pending transaction creation. It must become the authority for verified provider events before wallet crediting is enabled. `vtu` is feature-flagged off and needs durable idempotency/reconciliation. Keep those boundaries explicit: do not hide provider side effects in templates or generic wallet helpers.
