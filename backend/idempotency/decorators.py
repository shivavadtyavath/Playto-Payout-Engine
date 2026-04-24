"""
Idempotency decorator for DRF APIView methods.

How it works:
1. Validate the Idempotency-Key header is present and a valid UUID.
2. Look up an unexpired key (< 24h old) for this merchant.
3. If found, return the cached response immediately — no business logic runs.
4. If not found, execute the view and store the response.
5. Handle the race condition: if two concurrent requests both miss the lookup,
   only one INSERT will succeed (DB unique constraint). The loser catches
   IntegrityError and fetches the winner's stored response.

This guarantees exactly-once semantics for payout creation.
"""
import uuid
import logging
from functools import wraps
from datetime import timedelta

from django.db import IntegrityError
from django.utils.timezone import now
from rest_framework.response import Response

from .models import IdempotencyKey

logger = logging.getLogger(__name__)


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


def idempotent_view(view_method):
    """
    Decorator for a DRF APIView instance method (e.g. def post(self, request)).

    Usage:
        class MyView(APIView):
            @idempotent_view
            def post(self, request):
                ...
    """
    @wraps(view_method)
    def wrapper(self, request, *args, **kwargs):
        idempotency_key = request.headers.get('Idempotency-Key')

        if not idempotency_key or not is_valid_uuid(idempotency_key):
            return Response(
                {
                    'error': 'Idempotency-Key header is required and must be a valid UUID.',
                    'code': 'INVALID_IDEMPOTENCY_KEY',
                },
                status=400
            )

        merchant = getattr(request, 'merchant', None)
        if merchant is None:
            return Response(
                {'error': 'Authentication required.', 'code': 'UNAUTHENTICATED'},
                status=401
            )

        # Check for an existing unexpired key (< 24h old)
        expiry_cutoff = now() - timedelta(hours=24)
        existing = IdempotencyKey.objects.filter(
            merchant=merchant,
            key=idempotency_key,
            created_at__gte=expiry_cutoff,
        ).first()

        if existing:
            logger.info(
                "Idempotency cache hit: key=%s merchant=%s status=%s",
                idempotency_key, merchant.id, existing.status_code
            )
            return Response(existing.response_body, status=existing.status_code)

        # Execute the actual view method
        response = view_method(self, request, *args, **kwargs)

        # Store the response so future duplicate requests get the same answer.
        # The DB unique constraint on (merchant_id, key) is the safety net:
        # if two concurrent requests both miss the lookup above and both try
        # to INSERT, only one succeeds. The loser catches IntegrityError.
        try:
            IdempotencyKey.objects.create(
                merchant=merchant,
                key=idempotency_key,
                response_body=response.data,
                status_code=response.status_code,
            )
        except IntegrityError:
            # Another concurrent request already stored the response.
            # Fetch and return the stored response.
            logger.warning(
                "Idempotency IntegrityError (concurrent duplicate): key=%s merchant=%s",
                idempotency_key, merchant.id
            )
            stored = IdempotencyKey.objects.get(merchant=merchant, key=idempotency_key)
            return Response(stored.response_body, status=stored.status_code)

        return response

    return wrapper
