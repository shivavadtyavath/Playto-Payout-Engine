from rest_framework import serializers
from .models import Payout


class PayoutCreateSerializer(serializers.Serializer):
    """Input serializer for POST /api/v1/payouts/"""
    amount_paise = serializers.IntegerField(
        min_value=1,
        error_messages={
            'min_value': 'amount_paise must be a positive integer (minimum 1 paise).',
            'invalid': 'amount_paise must be an integer.',
        }
    )
    bank_account_id = serializers.UUIDField()


class PayoutResponseSerializer(serializers.ModelSerializer):
    """Output serializer for payout responses."""
    bank_account_id = serializers.UUIDField(source='bank_account.id')

    class Meta:
        model = Payout
        fields = ['id', 'amount_paise', 'bank_account_id', 'status', 'created_at', 'updated_at']
