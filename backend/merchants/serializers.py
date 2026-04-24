from rest_framework import serializers
from .models import Merchant, BankAccount


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'account_number', 'ifsc_code', 'account_holder', 'is_active', 'created_at']


class MerchantBalanceSerializer(serializers.Serializer):
    merchant_id = serializers.UUIDField()
    name = serializers.CharField()
    available_balance_paise = serializers.IntegerField()
    held_balance_paise = serializers.IntegerField()
