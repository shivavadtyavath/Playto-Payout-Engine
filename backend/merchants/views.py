from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import MerchantBalanceSerializer, BankAccountSerializer
from .auth import MerchantHeaderAuthentication
from ledger.queries import get_available_balance, get_held_balance


class MerchantMeView(APIView):
    authentication_classes = [MerchantHeaderAuthentication]

    def get(self, request):
        merchant = request.merchant
        data = {
            'merchant_id': merchant.id,
            'name': merchant.name,
            'available_balance_paise': get_available_balance(merchant),
            'held_balance_paise': get_held_balance(merchant),
        }
        serializer = MerchantBalanceSerializer(data)
        return Response(serializer.data)


class BankAccountListView(APIView):
    authentication_classes = [MerchantHeaderAuthentication]

    def get(self, request):
        accounts = request.merchant.bank_accounts.filter(is_active=True)
        serializer = BankAccountSerializer(accounts, many=True)
        return Response(serializer.data)
