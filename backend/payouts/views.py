"""
Payout API views.

The critical path for payout creation:
1. Validate idempotency key (decorator)
2. Validate input (serializer)
3. Validate bank account ownership
4. BEGIN TRANSACTION
5. SELECT FOR UPDATE on merchant's ledger rows (acquires row-level lock)
6. Compute available balance via DB aggregation
7. Check balance >= amount_paise (reject with 422 if not)
8. INSERT LedgerEntry (debit)
9. INSERT Payout (pending)
10. COMMIT
11. Enqueue Celery task
12. Return 201

The SELECT FOR UPDATE in step 5 is the key concurrency primitive.
It serializes concurrent balance checks for the same merchant.
"""
import logging

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from merchants.auth import MerchantHeaderAuthentication
from merchants.models import BankAccount
from ledger.models import LedgerEntry
from ledger.queries import get_available_balance
from idempotency.decorators import idempotent_view

from .models import Payout
from .serializers import PayoutCreateSerializer, PayoutResponseSerializer

logger = logging.getLogger(__name__)


class PayoutListCreateView(APIView):
    authentication_classes = [MerchantHeaderAuthentication]

    @idempotent_view
    def post(self, request):
        """
        Create a payout request.

        Requires Idempotency-Key header (UUID).
        Requires X-Merchant-ID header.
        """
        serializer = PayoutCreateSerializer(data=request.data)
        if not serializer.is_valid():
            errors = []
            for field, messages in serializer.errors.items():
                for msg in messages:
                    errors.append(f"{field}: {msg}")
            return Response(
                {'error': '; '.join(errors), 'code': 'VALIDATION_ERROR'},
                status=status.HTTP_400_BAD_REQUEST
            )

        amount_paise = serializer.validated_data['amount_paise']
        bank_account_id = serializer.validated_data['bank_account_id']
        merchant = request.merchant

        # Validate bank account belongs to this merchant
        try:
            bank_account = BankAccount.objects.get(
                id=bank_account_id,
                merchant=merchant,
                is_active=True,
            )
        except BankAccount.DoesNotExist:
            return Response(
                {
                    'error': 'Bank account not found or does not belong to this merchant.',
                    'code': 'INVALID_BANK_ACCOUNT',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Critical section: SELECT FOR UPDATE + balance check + debit + payout creation
        # All within a single atomic transaction.
        #
        # Why SELECT FOR UPDATE on LedgerEntry rows?
        # We lock the merchant's ledger rows before reading the balance.
        # This prevents two concurrent requests from both reading the same
        # balance, both passing the check, and both creating payouts that
        # together exceed the available balance (TOCTOU race condition).
        #
        # The lock is released when the transaction commits or rolls back.
        # The second concurrent request will block on SELECT FOR UPDATE until
        # the first transaction completes, then re-read the updated balance.
        with transaction.atomic():
            # Acquire row-level locks on all ledger entries for this merchant.
            # This serializes concurrent payout requests for the same merchant.
            locked_entries = LedgerEntry.objects.select_for_update().filter(
                merchant=merchant
            )
            # Force evaluation to actually acquire the locks
            list(locked_entries)

            available_balance = get_available_balance(merchant)

            if available_balance < amount_paise:
                return Response(
                    {
                        'error': (
                            f'Insufficient funds. Available: {available_balance} paise, '
                            f'Requested: {amount_paise} paise.'
                        ),
                        'code': 'INSUFFICIENT_FUNDS',
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            # Create the payout record
            payout = Payout.objects.create(
                merchant=merchant,
                bank_account=bank_account,
                amount_paise=amount_paise,
                status=Payout.PENDING,
            )

            # Create the debit ledger entry atomically with the payout
            LedgerEntry.objects.create(
                merchant=merchant,
                entry_type=LedgerEntry.DEBIT,
                amount_paise=amount_paise,
                description=f'Payout request {payout.id}',
                payout=payout,
            )

        # Enqueue background processing AFTER the transaction commits
        # so the worker always sees the committed payout record
        from .tasks import process_payout
        process_payout.delay(str(payout.id))

        logger.info(
            "Payout created: id=%s merchant=%s amount=%s",
            payout.id, merchant.id, amount_paise
        )

        response_serializer = PayoutResponseSerializer(payout)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        """List all payouts for the authenticated merchant."""
        merchant = getattr(request, 'merchant', None)
        if merchant is None:
            return Response(
                {'error': 'Authentication required.', 'code': 'UNAUTHENTICATED'},
                status=401
            )
        payouts = Payout.objects.filter(
            merchant=merchant
        ).order_by('-created_at')
        serializer = PayoutResponseSerializer(payouts, many=True)
        return Response(serializer.data)


class PayoutDetailView(APIView):
    authentication_classes = [MerchantHeaderAuthentication]

    def get(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id, merchant=request.merchant)
        except Payout.DoesNotExist:
            return Response(
                {'error': 'Payout not found.', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = PayoutResponseSerializer(payout)
        return Response(serializer.data)
