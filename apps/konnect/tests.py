from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CreativeProfile, PortfolioItem

User = get_user_model()


class PublicMarketplaceRouteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="designer", email="designer@example.com", password="StrongPass123!",
            role="creative",
        )
        self.profile = CreativeProfile.objects.create(
            user=self.user, headline="Brand designer", category="graphic_design",
        )
        self.project = PortfolioItem.objects.create(
            creative=self.profile, title="Brand mark", category="branding",
        )

    def test_public_pages_render_empty_and_populated_states(self):
        for name in ("home_feed", "discover", "hire_creative"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get(reverse("home_feed")), "Brand mark")
        self.assertContains(self.client.get(reverse("discover")), "Brand mark")

    def test_all_creative_categories_resolve(self):
        for value, _label in CreativeProfile.CATEGORY_CHOICES:
            response = self.client.get(reverse("hire_creative"), {"category": value})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["selected_category"], value)

    def test_hire_category_preserves_search_query(self):
        response = self.client.get(reverse("hire_creative"), {"q": "brand"})
        self.assertContains(response, "category=graphic_design&amp;q=brand")

    def test_discover_category_filters_top_creatives(self):
        other = User.objects.create_user(
            username="developer", email="developer@example.com", password="StrongPass123!",
            role="creative",
        )
        other_profile = CreativeProfile.objects.create(
            user=other, headline="Developer", category="web_development",
        )
        PortfolioItem.objects.create(
            creative=other_profile, title="Website", category="web_development",
        )
        response = self.client.get(reverse("discover"), {"category": "branding"})
        self.assertEqual(list(response.context["top_creatives"]), [self.profile])

    def test_hidden_project_is_not_publicly_accessible(self):
        self.project.is_reported_hidden = True
        self.project.save(update_fields=["is_reported_hidden"])
        response = self.client.get(reverse("project_detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 404)
