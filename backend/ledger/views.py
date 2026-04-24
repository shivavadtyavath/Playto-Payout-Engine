from rest_framework.views import APIView
from rest_framework.response import Response
from merchants.auth import MerchantHeaderAuthentication
from .models import LedgerEntry
from .serializers import LedgerEntrySerializer


class LedgerEntryListView(APIView):
    authentication_classes = [MerchantHeaderAuthentication]

    def get(self, request):
        entries = LedgerEntry.objects.filter(
            merchant=request.merchant
        ).order_by('-created_at')[:50]
        serializer = LedgerEntrySerializer(entries, many=True)
        return Response(serializer.data)
