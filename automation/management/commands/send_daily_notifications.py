from django.core.management.base import BaseCommand

from automation.services import run_daily_notifications


class Command(BaseCommand):
    help = (
        "Send the day's batch of role-personalized daily notifications "
        "(students, creatives, customers). Safe to run more than once a "
        "day: already-sent notifications are never duplicated. Intended "
        "to be triggered once a day by cron, Celery Beat, or "
        "run_automation_scheduler."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Send even if automation is disabled or already ran today (useful for testing).",
        )

    def handle(self, *args, **options):
        stats = run_daily_notifications(force=options["force"])
        if stats.get("skipped"):
            self.stdout.write(self.style.WARNING(f"Skipped: {stats['reason']}"))
            return
        self.stdout.write(self.style.SUCCESS(
            f"Sent {stats['sent']} notifications ({stats['emails_sent']} emails) for {stats['date']}. "
            f"Muted-category skips: {stats['skipped_muted']}, duplicate skips: {stats['skipped_duplicate']}."
        ))
