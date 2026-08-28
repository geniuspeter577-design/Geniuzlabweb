import uuid
from django.conf import settings
from django.db import models


class Transaction(models.Model):
    PROVIDER_CHOICES = [
        ("paystack", "Paystack"),
        ("flutterwave", "Flutterwave"),
        ("monnify", "Monnify"),
        ("wallet", "Wallet Balance"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Successful"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    PURPOSE_CHOICES = [
        ("wallet_funding", "Wallet Funding"),
        ("subscription", "Subscription"),
        ("service", "Creative Service"),
        ("job_deposit", "Job Deposit"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    reference = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="paystack")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default="other")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="NGN")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} - {self.user} - {self.amount} ({self.status})"

    def mark_success(self):
        self.status = "success"
        self.save(update_fields=["status", "updated_at"])
