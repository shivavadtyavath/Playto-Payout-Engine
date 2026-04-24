import uuid
from django.db import models


class Payout(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.PROTECT,
        related_name='payouts'
    )
    bank_account = models.ForeignKey(
        'merchants.BankAccount',
        on_delete=models.PROTECT,
        related_name='payouts'
    )
    # All monetary values stored as integers in paise. Never FloatField or DecimalField.
    amount_paise = models.BigIntegerField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    # Tracks how many times this payout has been retried after getting stuck in processing
    retry_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payouts'
        indexes = [
            # For dashboard payout list filtered by merchant + status
            models.Index(fields=['merchant', 'status'], name='payout_merchant_status_idx'),
            # For stuck-payout detection: find processing payouts older than 30s
            models.Index(fields=['status', 'updated_at'], name='payout_status_updated_idx'),
        ]

    def __str__(self):
        return f"Payout({self.id}) {self.amount_paise} paise [{self.status}]"
