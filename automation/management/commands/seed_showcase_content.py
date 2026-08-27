"""
Seed a handful of demo showcase entries (portfolio items + motion reels) so
the public-facing marketing pages don't look like an empty new install.

Idempotent — safe to re-run; it only creates records that don't exist yet
and skips entirely once the demo account already has portfolio items.

This does NOT use anyone's personal photos — the images are the procedurally
generated, on-brand placeholder graphics already shipped in
static/images/generated/, copied into MEDIA so they can be attached to the
real ImageField/FileField on each model, exactly the way a real user's
upload would be stored.

Run with: python manage.py seed_showcase_content
"""
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from konnect.models import CreativeProfile, PortfolioItem
from motion.models import MotionShowcase

DEMO_USERNAME = "geniuzlab_studio"
GENERATED_DIR = settings.BASE_DIR / "static" / "images" / "generated"

PORTFOLIO_SEED = [
    ("Brand Identity System", "Complete logo, colour palette and brand guideline set delivered for a growing retail brand.", "portfolio_branding.png"),
    ("Cinematic Product Reel", "15-second vertical product edit built for a paid social campaign.", "portfolio_video.png"),
    ("SaaS Marketing Site", "Responsive marketing site built and shipped end-to-end for a startup launch.", "portfolio_webdev.png"),
]

MOTION_SEED = [
    ("Launch Day Recap", "Highlight reel cut from a full-day brand launch event.", "portfolio_video.png"),
    ("Weekly Vlog Edit", "Fast-paced retention-focused edit for a creator's weekly upload.", "hero_motion.png"),
    ("Ad Campaign Cutdown", "15s/30s cutdowns of a longer brand film for paid placement.", "course_video_editing.png"),
]


class Command(BaseCommand):
    help = "Seed demo portfolio + motion showcase content using the generated brand imagery (idempotent)."

    def handle(self, *args, **options):
        with transaction.atomic():
            user, user_created = User.objects.get_or_create(
                username=DEMO_USERNAME,
                defaults={
                    "email": "studio@geniuzlab.com",
                    "first_name": "GeniuzLab",
                    "last_name": "Studio",
                    "role": "creative",
                    "is_active": True,
                },
            )
            if user_created:
                user.set_unusable_password()
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created demo user '{DEMO_USERNAME}'"))

            profile, _ = CreativeProfile.objects.get_or_create(
                user=user,
                defaults={
                    "headline": "GeniuzLab in-house creative studio",
                    "category": "other",
                    "bio": "Example work showcased by the GeniuzLab team.",
                    "is_available": False,
                },
            )

            created_count = 0
            if not profile.portfolio_items.exists():
                for title, description, filename in PORTFOLIO_SEED:
                    item = PortfolioItem(creative=profile, title=title, description=description)
                    src = GENERATED_DIR / filename
                    if src.exists():
                        with open(src, "rb") as f:
                            item.image.save(filename, File(f), save=False)
                    item.save()
                    created_count += 1
            else:
                self.stdout.write("Portfolio items already exist for demo profile — skipping portfolio seed.")

            motion_created = 0
            if not MotionShowcase.objects.exists():
                for title, description, filename in MOTION_SEED:
                    show = MotionShowcase(title=title, description=description)
                    src = GENERATED_DIR / filename
                    if src.exists():
                        with open(src, "rb") as f:
                            show.thumbnail.save(filename, File(f), save=False)
                    show.save()
                    motion_created += 1
            else:
                self.stdout.write("MotionShowcase already has entries — skipping motion seed.")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Portfolio items created: {created_count}. Motion showcase entries created: {motion_created}."
        ))
