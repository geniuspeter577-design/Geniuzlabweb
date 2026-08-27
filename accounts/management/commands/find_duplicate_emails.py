from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):
    """Run this BEFORE applying the migration that adds unique=True to
    User.email (see accounts/models.py). It never modifies data — it only
    reports rows that would violate the new constraint, so you can decide
    how to resolve each one (merge accounts, rename one to a placeholder,
    contact the user, etc.) with full context first.

    Usage:
        python manage.py find_duplicate_emails
    """

    help = "Report user accounts that share the same (non-empty) email address."

    def handle(self, *args, **options):
        User = get_user_model()
        dupes = (
            User.objects.exclude(email="")
            .values("email")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
            .order_by("-count")
        )

        if not dupes:
            self.stdout.write(self.style.SUCCESS(
                "No duplicate emails found — safe to run `manage.py migrate`."
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"Found {len(dupes)} email address(es) shared by more than one account:\n"
        ))
        for row in dupes:
            users = User.objects.filter(email=row["email"]).order_by("date_joined")
            self.stdout.write(f"  {row['email']}  ({row['count']} accounts)")
            for u in users:
                self.stdout.write(
                    f"    - id={u.id} username={u.username!r} date_joined={u.date_joined}"
                )
        self.stdout.write(
            "\nResolve each of these (e.g. clear/replace the email on the "
            "older duplicate accounts) before running `manage.py migrate`, "
            "or the migration adding the unique constraint will fail."
        )
