# Operations Runbook

## Local setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export GENIUZLAB_DEBUG=True
export GENIUZLAB_SECRET_KEY=local-development-only
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
python backend/manage.py createsuperuser
python backend/manage.py runserver
```

The repository currently has no committed `.env.example`. Never commit real credentials. Use environment variables or a local ignored `.env` file.

## Production-required configuration

Set `GENIUZLAB_SECRET_KEY`, `GENIUZLAB_ALLOWED_HOSTS`, `GENIUZLAB_DATABASE_URL`, `GENIUZLAB_CSRF_TRUSTED_ORIGINS`, and `GENIUZLAB_EMAIL_HOST` plus SMTP credentials. Keep `GENIUZLAB_DEBUG=False`. Use Postgres or another supported concurrent database, not SQLite.

Optional integrations include Redis (`GENIUZLAB_REDIS_CACHE_URL`), Celery broker/result settings, payment provider keys, VTpass keys, and AI provider keys. `FEATURE_VTU_ENABLED` is false by default.

## Pre-deploy checks

```bash
python backend/manage.py check --deploy
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py test --noinput
python backend/manage.py collectstatic --noinput
```

Apply migrations to staging, verify email delivery, exercise provider sandbox callbacks, and confirm backups can be restored before production.

## Scheduled automation

Use one scheduler strategy only:

- Celery: `celery -A geniuzlab worker -l info` and `celery -A geniuzlab beat -l info`
- Built-in: `python manage.py run_automation_scheduler`
- Cron: invoke the daily management commands at the desired time

Do not run multiple strategies simultaneously unless duplicate behavior has been deliberately tested; database uniqueness protects many duplicates but does not make delivery costs or logs disappear.

## Static and media

Run `collectstatic` for WhiteNoise's manifest storage. In production, serve `MEDIA_ROOT` through a durable object-storage/web-server strategy; uploaded media must not depend on an ephemeral application filesystem.
