"""
Balance query functions.

CRITICAL: All balance calculations use database-level aggregation (Django ORM Sum()).
We never fetch rows and do Python arithmetic — that would be incorrect under concurrent
writes and would not benefit from database-level locking.
"""
from django.db.models import Sum, Q
from .models import LedgerEntry


def get_available_balance(merchant) -> int:
    """
    Compute available balance as a single DB-level aggregation.

    Query: SELECT
        SUM(amount_paise) FILTER (WHERE entry_type = 'credit') AS credits,
        SUM(amount_paise) FILTER (WHERE entry_type = 'debit')  AS debits
    FROM ledger_entries
    WHERE merchant_id = %s

    Returns credits - debits in paise (integer).
    """
    agg = LedgerEntry.objects.filter(merchant=merchant).aggregate(
        credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
        debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT)),
    )
    return (agg['credits'] or 0) - (agg['debits'] or 0)


def get_held_balance(merchant) -> int:
    """
    Compute held balance: sum of payout amounts in pending or processing state.

    Held balance represents funds that have been debited from the ledger but
    not yet settled (completed) or returned (failed).
    """
    from payouts.models import Payout
    result = Payout.objects.filter(
        merchant=merchant,
        status__in=[Payout.PENDING, Payout.PROCESSING]
    ).aggregate(total=Sum('amount_paise'))
    return result['total'] or 0
