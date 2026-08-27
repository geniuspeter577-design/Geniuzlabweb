"""Celery application for GeniuzLab.

Requires a running broker (Redis by default) and the `celery` package —
see requirements.txt. Start in production with:

    celery -A geniuzlab worker -l info
    celery -A geniuzlab beat -l info

The beat schedule below wakes up once a minute and asks the automation
engine "is it time yet, and has today's batch already gone out?" — the
actual send time is read live from AutomationSettings each run, so
changing the time in the admin dashboard takes effect immediately with
no restart required.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geniuzlab.settings")

app = Celery("geniuzlab")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-and-send-daily-notifications": {
        "task": "automation.tasks.check_and_send_daily",
        "schedule": crontab(minute="*"),
    },
}
