import uuid
from django.db import models


class IdempotencyKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.CASCADE,
        related_name='idempotency_keys'
    )
    # The UUID string supplied by the client in the Idempotency-Key header
    key = models.CharField(max_length=36)
    # Serialized HTTP response body stored as JSON
    response_body = models.JSONField()
    # HTTP status code of the original response
    status_code = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'idempotency_keys'
        constraints = [
            # This unique constraint is the safety net for concurrent duplicate requests.
            # Even if two requests race past the initial lookup, only one INSERT will succeed.
            models.UniqueConstraint(
                fields=['merchant', 'key'],
                name='unique_idempotency_key_per_merchant'
            )
        ]
        indexes = [
            models.Index(fields=['merchant', 'key'], name='idempotency_merchant_key_idx'),
            # For expiry cleanup queries
            models.Index(fields=['created_at'], name='idempotency_created_at_idx'),
        ]

    def __str__(self):
        return f"IdempotencyKey({self.key}) for merchant {self.merchant_id}"
