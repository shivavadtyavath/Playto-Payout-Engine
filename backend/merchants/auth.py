from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Merchant


class MerchantHeaderAuthentication(BaseAuthentication):
    """
    Simple authentication that reads X-Merchant-ID header.
    In production this would be replaced with JWT/OAuth.
    """

    def authenticate(self, request):
        merchant_id = request.headers.get('X-Merchant-ID')
        if not merchant_id:
            return None  # Let other authenticators try, or fall through to permission check

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except (Merchant.DoesNotExist, ValueError):
            raise AuthenticationFailed('Merchant not found or invalid X-Merchant-ID header.')

        # Attach merchant directly to request for convenience
        request.merchant = merchant
        return (merchant, None)

    def authenticate_header(self, request):
        return 'X-Merchant-ID'
