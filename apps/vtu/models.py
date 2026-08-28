from django.conf import settings
from django.db import models


class VTUOrder(models.Model):
    """A single VTU purchase (airtime, data, cable TV, electricity, WAEC/JAMB pin).

    One unified model backs every service type so history, receipts and
    requery/status-check logic don't have to be duplicated per service.
    """

    SERVICE_AIRTIME = "airtime"
    SERVICE_DATA = "data"
    SERVICE_CABLE = "cable"
    SERVICE_ELECTRICITY = "electricity"
    SERVICE_EDUCATION = "education"

    SERVICE_CHOICES = [
        (SERVICE_AIRTIME, "Airtime"),
        (SERVICE_DATA, "Data"),
        (SERVICE_CABLE, "Cable TV"),
        (SERVICE_ELECTRICITY, "Electricity"),
        (SERVICE_EDUCATION, "Education (WAEC/JAMB)"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SUCCESSFUL = "successful"
    STATUS_FAILED = "failed"
    STATUS_REVERSED = "reversed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESSFUL, "Successful"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REVERSED, "Reversed (refunded to wallet)"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vtu_orders"
    )
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    service_id = models.CharField(
        max_length=50,
        help_text="VTpass serviceID, e.g. 'mtn', 'mtn-data', 'dstv', 'ikeja-electric', 'waec-registration'.",
    )
    variation_code = models.CharField(max_length=50, blank=True)
    recipient = models.CharField(
        max_length=50,
        help_text="Phone number, smartcard/IUC number, or meter number depending on service.",
    )
    recipient_name = models.CharField(
        max_length=150, blank=True, help_text="Verified customer name (cable/electricity)."
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    request_id = models.CharField(max_length=64, unique=True)
    provider_transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    response_message = models.CharField(max_length=255, blank=True)
    raw_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_service_type_display()} · {self.recipient} · ₦{self.amount} ({self.status})"

    @property
    def is_final(self):
        return self.status in (self.STATUS_SUCCESSFUL, self.STATUS_FAILED, self.STATUS_REVERSED)
