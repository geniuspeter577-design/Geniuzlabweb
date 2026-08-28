from django.conf import settings
from django.db import models


class SubscriptionPlan(models.Model):
    CATEGORY_CHOICES = [
        ("data", "Data Bundle"),
        ("airtime", "Airtime"),
        ("tv", "TV Subscription"),
        ("electricity", "Electricity"),
        ("premium", "GeniuzLab Premium"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="premium")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - ₦{self.price}"


class UserSubscription(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("expired", "Expired"), ("pending", "Pending")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name="subscribers")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
