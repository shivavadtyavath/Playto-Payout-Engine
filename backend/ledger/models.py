import uuid
from django.db import models


class LedgerEntry(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'
    ENTRY_TYPE_CHOICES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.PROTECT,
        related_name='ledger_entries'
    )
    entry_type = models.CharField(max_length=6, choices=ENTRY_TYPE_CHOICES)
    # All monetary values stored as integers in paise. Never FloatField or DecimalField.
    amount_paise = models.BigIntegerField()
    description = models.TextField(blank=True)
    payout = models.ForeignKey(
        'payouts.Payout',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='ledger_entries'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger_entries'
        indexes = [
            # For paginated ledger fetch ordered by time
            models.Index(fields=['merchant', 'created_at'], name='ledger_merchant_time_idx'),
            # For balance aggregation filter by entry type
            models.Index(fields=['merchant', 'entry_type'], name='ledger_merchant_type_idx'),
        ]

    def __str__(self):
        return f"{self.entry_type.upper()} {self.amount_paise} paise for {self.merchant_id}"
