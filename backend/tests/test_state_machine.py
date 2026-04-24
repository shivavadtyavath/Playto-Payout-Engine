"""
State machine tests.

Property 13: State Machine Transition Enforcement
Feature: playto-payout-engine
"""
import uuid
from django.test import TestCase
from unittest.mock import patch

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout
from payouts.state_machine import transition_payout, InvalidTransitionError, VALID_TRANSITIONS


def make_payout(status='pending'):
    merchant = Merchant.objects.create(
        name='SM Test',
        email=f'sm-{uuid.uuid4()}@test.com',
    )
    bank_account = BankAccount.objects.create(
        merchant=merchant,
        account_number='1111111111',
        ifsc_code='HDFC0000001',
        account_holder='SM Test',
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        entry_type=LedgerEntry.CREDIT,
        amount_paise=100_000,
        description='Test credit',
    )
    return Payout.objects.create(
        merchant=merchant,
        bank_account=bank_account,
        amount_paise=10_000,
        status=status,
    )


class StateMachineTest(TestCase):
    """
    # Feature: playto-payout-engine, Property 13: State Machine Transition Enforcement
    """

    def test_legal_transition_pending_to_processing(self):
        payout = make_payout('pending')
        transition_payout(payout, 'processing')
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'processing')

    def test_legal_transition_processing_to_completed(self):
        payout = make_payout('processing')
        transition_payout(payout, 'completed')
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'completed')

    def test_legal_transition_processing_to_failed(self):
        payout = make_payout('processing')
        transition_payout(payout, 'failed')
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'failed')

    def test_illegal_completed_to_pending(self):
        payout = make_payout('completed')
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout, 'pending')
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'completed')  # unchanged

    def test_illegal_failed_to_completed(self):
        payout = make_payout('failed')
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout, 'completed')
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'failed')  # unchanged

    def test_illegal_pending_to_failed(self):
        """pending → failed is illegal (must go through processing)."""
        payout = make_payout('pending')
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout, 'failed')

    def test_illegal_pending_to_completed(self):
        payout = make_payout('pending')
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout, 'completed')

    def test_illegal_completed_to_failed(self):
        payout = make_payout('completed')
        with self.assertRaises(InvalidTransitionError):
            transition_payout(payout, 'failed')

    def test_all_illegal_transitions_raise_error(self):
        """
        # Feature: playto-payout-engine, Property 13: State Machine Transition Enforcement
        Exhaustive check: every (from, to) pair not in VALID_TRANSITIONS raises InvalidTransitionError.
        """
        all_states = ['pending', 'processing', 'completed', 'failed']
        for from_state in all_states:
            for to_state in all_states:
                if to_state in VALID_TRANSITIONS.get(from_state, []):
                    continue  # legal transition, skip
                payout = make_payout(from_state)
                with self.assertRaises(InvalidTransitionError, msg=f"{from_state} → {to_state} should be illegal"):
                    transition_payout(payout, to_state)

    def test_timestamp_updated_on_transition(self):
        """
        # Feature: playto-payout-engine, Property 15: Timestamp Updated on Every Transition
        updated_at must be strictly greater after a valid transition.
        """
        import time
        payout = make_payout('pending')
        before = payout.updated_at
        time.sleep(0.01)  # ensure clock advances
        transition_payout(payout, 'processing')
        payout.refresh_from_db()
        self.assertGreater(payout.updated_at, before)
