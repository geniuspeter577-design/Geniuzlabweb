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
        ("course_enrollment", "Course Enrollment"),
        ("subscription", "Subscription"),
        ("service", "Creative Service"),
        ("job_deposit", "Job Deposit"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    course = models.ForeignKey(
        "academy.Course", null=True, blank=True, on_delete=models.PROTECT,
        related_name="payment_transactions",
    )
    reference = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    provider_reference = models.CharField(max_length=100, blank=True)
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
        from django.db import transaction

        with transaction.atomic():
            locked = Transaction.objects.select_for_update().select_related("course").get(pk=self.pk)
            if locked.status == "success":
                self.status = locked.status
                return False
            if locked.status != "pending":
                return False
            if locked.course_id and locked.amount != locked.course.price:
                raise ValueError("Course payment amount no longer matches the course price.")

            if locked.course_id:
                from apps.academy.models import Enrollment
                Enrollment.objects.get_or_create(user=locked.user, course=locked.course)
            elif locked.purpose == "wallet_funding":
                from apps.wallet.models import Wallet
                wallet, _ = Wallet.objects.get_or_create(user=locked.user)
                wallet.credit(
                    locked.amount,
                    reference=locked.reference,
                    description=f"Payment funding via {locked.get_provider_display()}",
                )

            locked.status = "success"
            locked.save(update_fields=["status", "updated_at"])
            self.status = locked.status
            return True
