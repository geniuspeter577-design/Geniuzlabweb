from django.core.management.base import BaseCommand

from automation.models import DailyMessageTemplate

DEFAULT_TEMPLATES = [
    # Students
    ("student", "learning_reminder", "Hey {first_name}, jump back into your course today — a little progress every day adds up.", "/academy/"),
    ("student", "academy_update", "Geniuz Academy has fresh lessons and resources waiting for you.", "/academy/"),
    ("student", "new_course", "New courses just landed in the Academy — come see what's new.", "/academy/"),
    ("student", "ai_tip", "AI tip of the day: try asking your AI assistant to summarize your notes before a quiz.", "/academy/"),
    ("student", "motivation", "{first_name}, small steps every day lead to big skills. Keep going!", "/academy/"),
    # Instructors (share the student/academy category set)
    ("instructor", "academy_update", "Your Academy dashboard has updates worth checking today.", "/academy/"),
    ("instructor", "motivation", "{first_name}, your students are counting on you — have a great teaching day.", "/academy/"),
    # Creatives
    ("creative", "job_opportunity", "New jobs matching your skills were posted today — take a look.", "/jobs/"),
    ("creative", "client_request", "You may have new client requests waiting in your dashboard.", "/service-requests/"),
    ("creative", "portfolio_tip", "Portfolio tip: adding 2-3 recent projects boosts client trust significantly.", "/my-creative-profile/"),
    ("creative", "ai_tool", "Try GeniuzLab's AI creative tools to speed up your next project.", "/dashboard/"),
    ("creative", "productivity", "{first_name}, block out your first hour today for deep, focused work.", "/dashboard/"),
    # Customers
    ("customer", "hire_suggestion", "Looking for help on a project? Browse top-rated creatives on GeniuzLab.", "/hire-creative/"),
    ("customer", "recommended_creative", "We found creatives that match what you've been looking for.", "/hire-creative/"),
    ("customer", "platform_update", "GeniuzLab has new features — check out what's new on your dashboard.", "/dashboard/"),
    ("customer", "wallet_reminder", "{first_name}, don't forget to keep your wallet funded for smooth transactions.", "/wallet/"),
    ("customer", "promo", "Special offers are live on GeniuzSubs today — grab a great deal.", "/subs/"),
]


class Command(BaseCommand):
    help = "Seed the default set of daily notification templates (idempotent — safe to re-run)."

    def handle(self, *args, **options):
        created_count = 0
        for role, category, message, link in DEFAULT_TEMPLATES:
            _, created = DailyMessageTemplate.objects.get_or_create(
                role=role, category=category,
                defaults={"message": message, "link": link, "is_active": True},
            )
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {created_count} new templates created "
            f"({len(DEFAULT_TEMPLATES) - created_count} already existed)."
        ))
