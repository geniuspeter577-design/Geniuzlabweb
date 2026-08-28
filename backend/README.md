# Backend

This directory owns the Django server and its project configuration.

## Current state

The Django project package now lives here:

- `backend/manage.py`
- `backend/geniuzlab/`

Templates and static files remain at the repository root temporarily because
their discovery paths are being migrated separately. The current locations are
`templates/` and `static/`; first-party apps now live under `apps/`.

Root `geniuzlab/` is now a compatibility package. Existing
`DJANGO_SETTINGS_MODULE=geniuzlab.settings` deployments continue to work, but
new deployments should use `backend.geniuzlab.settings`.

## Intended ownership

- Django project configuration, ASGI/WSGI, Celery, and management commands
- HTTP/API composition and server-side rendering
- persistence, domain services, and integrations
- backend-owned templates and static assets after extraction

## Compatibility entry points

The following paths are ready for deployment tooling today:

- `python backend/manage.py ...`
- `backend.wsgi:application`
- `backend.asgi:application`

The root entry points remain compatibility aliases. Migration files and
serialized validator paths still use `geniuzlab.validators`, so that wrapper
must remain until those historical migration references are intentionally
revised.
