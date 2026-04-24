"""
Celery task tests: payout processing, retry logic, force-fail.
"""
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from ledger.queries import get_available_balance
from payouts.models import Payout
from payouts.tasks import process_payout, force_fail_payout, retry_payout


def make_payout_with_merchant(status='pending', amount_paise=10_000, retry_count=0):
    merchant = Merchant.objects.create(
        name='Task Test',
        email=f'task-{uuid.uuid4()}@test.com',
    )
    bank_account = BankAccount.objects.create(
        merchant=merchant,
        account_number='1234567890',
        ifsc_code='HDFC0001234',
        account_holder='Task Test',
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        entry_type=LedgerEntry.CREDIT,
        amount_paise=amount_paise * 2,
        description='Test credit',
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        entry_type=LedgerEntry.DEBIT,
        amount_paise=amount_paise,
        description='Test debit (simulating held funds)',
    )
    payout = Payout.objects.create(
        merchant=merchant,
        bank_account=bank_account,
        amount_paise=amount_paise,
        status=status,
        retry_count=retry_count,
    )
    return payout, merchant


class ProcessPayoutTest(TestCase):

    def test_completed_outcome_transitions_to_completed(self):
        payout, merchant = make_payout_with_merchant('pending')
        with patch('random.choices', return_value=['completed']):
            process_payout(str(payout.id))
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'completed')

    def test_failed_outcome_transitions_to_failed_and_refunds(self):
        """
        # Feature: playto-payout-engine, Property 4: Failed Payout Refund Atomicity
        """
        payout, merchant = make_payout_with_merchant('pending', amount_paise=10_000)
        balance_before = get_available_balance(merchant)

        with patch('random.choices', return_value=['failed']):
            process_payout(str(payout.id))

        payout.refresh_from_db()
        self.assertEqual(payout.status, 'failed')

        # Credit refund must exist
        refund = LedgerEntry.objects.filter(
            merchant=merchant,
            entry_type=LedgerEntry.CREDIT,
            payout=payout,
        )
        self.assertEqual(refund.count(), 1)
        self.assertEqual(refund.first().amount_paise, 10_000)

        # Balance restored
        balance_after = get_available_balance(merchant)
        self.assertEqual(balance_after, balance_before + 10_000)

    def test_hung_outcome_stays_in_processing(self):
        payout, _ = make_payout_with_merchant('pending')
        with patch('random.choices', return_value=['hung']):
            process_payout(str(payout.id))
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'processing')

    def test_completed_transition_creates_no_ledger_entry(self):
        """
        # Feature: playto-payout-engine, Property 14: Completed Transition Creates No Ledger Entry
        """
        payout, merchant = make_payout_with_merchant('pending')
        count_before = LedgerEntry.objects.filter(merchant=merchant).count()

        with patch('random.choices', return_value=['completed']):
            process_payout(str(payout.id))

        count_after = LedgerEntry.objects.filter(merchant=merchant).count()
        self.assertEqual(count_after, count_before)

    def test_already_processing_payout_is_skipped(self):
        """Guard against double-processing."""
        payout, _ = make_payout_with_merchant('processing')
        with patch('random.choices', return_value=['completed']) as mock_choices:
            process_payout(str(payout.id))
        # random.choices should not be called since we returned early
        mock_choices.assert_not_called()
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'processing')


class ForceFailPayoutTest(TestCase):

    def test_force_fail_transitions_to_failed_and_refunds(self):
        payout, merchant = make_payout_with_merchant('processing', amount_paise=5_000)
        balance_before = get_available_balance(merchant)

        force_fail_payout(str(payout.id))

        payout.refresh_from_db()
        self.assertEqual(payout.status, 'failed')

        refund = LedgerEntry.objects.filter(
            merchant=merchant,
            entry_type=LedgerEntry.CREDIT,
            payout=payout,
        )
        self.assertEqual(refund.count(), 1)
        self.assertEqual(refund.first().amount_paise, 5_000)

    def test_force_fail_skips_non_processing_payout(self):
        payout, _ = make_payout_with_merchant('completed')
        force_fail_payout(str(payout.id))
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'completed')  # unchanged


class RetryPayoutTest(TestCase):

    def test_retry_increments_count_and_resets_to_pending(self):
        payout, _ = make_payout_with_merchant('processing', retry_count=1)

        with patch('payouts.tasks.process_payout.delay') as mock_delay:
            retry_payout(str(payout.id))

        payout.refresh_from_db()
        self.assertEqual(payout.status, 'pending')
        self.assertEqual(payout.retry_count, 2)
        mock_delay.assert_called_once_with(str(payout.id))

    def test_retry_skips_non_processing_payout(self):
        payout, _ = make_payout_with_merchant('completed', retry_count=0)

        with patch('payouts.tasks.process_payout.delay') as mock_delay:
            retry_payout(str(payout.id))

        mock_delay.assert_not_called()
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'completed')
