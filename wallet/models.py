from decimal import Decimal

from django.conf import settings
from django.db import models, transaction


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s wallet - ₦{self.balance}"

    def credit(self, amount, reference="", description=""):
        amount = Decimal(amount)
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)
            wallet.balance += amount
            wallet.save(update_fields=["balance", "updated_at"])
            WalletTransaction.objects.create(
                wallet=wallet, amount=amount, type="credit",
                reference=reference, description=description,
            )
            self.balance = wallet.balance

    def debit(self, amount, reference="", description=""):
        # select_for_update locks this wallet's row for the duration of the
        # transaction, so a concurrent debit on the same wallet has to wait
        # rather than reading the same (potentially stale) balance — without
        # this, two near-simultaneous purchases could both pass the
        # insufficient-funds check against the same starting balance and
        # push it negative.
        amount = Decimal(amount)
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=self.pk)
            if amount > wallet.balance:
                raise ValueError("Insufficient wallet balance")
            wallet.balance -= amount
            wallet.save(update_fields=["balance", "updated_at"])
            WalletTransaction.objects.create(
                wallet=wallet, amount=amount, type="debit",
                reference=reference, description=description,
            )
            self.balance = wallet.balance


class WalletTransaction(models.Model):
    TYPE_CHOICES = [("credit", "Credit"), ("debit", "Debit")]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="entries")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    reference = models.CharField(max_length=64, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} of ₦{self.amount} on {self.wallet.user.username}"
