# Import the Celery app so `shared_task` decorators (used by automation/tasks.py)
# register correctly whenever Django starts. Safe no-op if celery isn't installed
# yet — the rest of the site (including the in-process scheduler fallback and
# plain cron) works fine without it.
try:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
except ImportError:
    pass
