from django.core.management.base import BaseCommand

from apps.automation.services import run_daily_bible_verse


class Command(BaseCommand):
    help = (
        "Send today's Bible verse to every user who hasn't opted out. Safe to "
        "run more than once a day: already-sent verses are never duplicated. "
        "Intended to be triggered once a day by cron, Celery Beat, or "
        "run_automation_scheduler alongside send_daily_notifications."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Send even if the feature is disabled (useful for testing).",
        )

    def handle(self, *args, **options):
        stats = run_daily_bible_verse(force=options["force"])
        if stats.get("skipped"):
            self.stdout.write(self.style.WARNING(f"Skipped: {stats['reason']}"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Sent '{stats['verse']}' to {stats['sent']} users for {stats['date']}. "
            f"Muted-category skips: {stats['skipped_muted']}, duplicate skips: {stats['skipped_duplicate']}."
        ))
