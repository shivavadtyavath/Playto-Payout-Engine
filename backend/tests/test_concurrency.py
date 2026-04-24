"""
Concurrency test: two simultaneous payout requests on insufficient balance.

Property 12: Concurrency Safety — No Negative Balance
Feature: playto-payout-engine

This is the most important test in the suite. It proves that SELECT FOR UPDATE
prevents the TOCTOU (time-of-check/time-of-use) race condition.

Scenario:
  - Merchant has 10,000 paise (₹100)
  - Two concurrent requests each for 7,000 paise (₹70)
  - Combined: 14,000 paise > 10,000 paise available
  - Expected: exactly one 201, exactly one 422
  - Invariant: balance never goes negative
"""
import threading
import uuid
from django.test import TestCase, Client, TransactionTestCase

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from ledger.queries import get_available_balance
from payouts.models import Payout


def create_merchant_with_balance(balance_paise: int):
    """Helper: create a merchant with a given opening credit balance."""
    merchant = Merchant.objects.create(
        name='Test Merchant',
        email=f'test-{uuid.uuid4()}@example.com',
    )
    bank_account = BankAccount.objects.create(
        merchant=merchant,
        account_number='1234567890',
        ifsc_code='HDFC0001234',
        account_holder='Test Merchant',
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        entry_type=LedgerEntry.CREDIT,
        amount_paise=balance_paise,
        description='Opening balance for test',
    )
    return merchant, bank_account


class ConcurrencyTest(TransactionTestCase):
    """
    Uses TransactionTestCase (not TestCase) because SELECT FOR UPDATE
    requires real transactions that can be committed and rolled back
    independently across threads. TestCase wraps everything in a single
    transaction that is never committed, which breaks locking semantics.
    """

    def test_concurrent_payouts_no_negative_balance(self):
        """
        # Feature: playto-payout-engine, Property 12: Concurrency Safety — No Negative Balance

        Two concurrent 7,000 paise requests on a 10,000 paise balance.
        Exactly one must succeed (201), the other must be rejected (422).
        Balance must never go negative.
        """
        merchant, bank_account = create_merchant_with_balance(10_000)

        results = []
        errors = []

        def submit_payout(amount_paise):
            client = Client()
            try:
                resp = client.post(
                    '/api/v1/payouts/',
                    data={'amount_paise': amount_paise, 'bank_account_id': str(bank_account.id)},
                    content_type='application/json',
                    HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
                    HTTP_X_MERCHANT_ID=str(merchant.id),
                )
                results.append(resp.status_code)
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=submit_payout, args=(7_000,))
        t2 = threading.Thread(target=submit_payout, args=(7_000,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [], f"Unexpected errors: {errors}")
        self.assertEqual(len(results), 2, "Expected exactly 2 responses")

        success_count = results.count(201)
        rejected_count = results.count(422)

        self.assertEqual(success_count, 1, f"Expected exactly 1 success, got: {results}")
        self.assertEqual(rejected_count, 1, f"Expected exactly 1 rejection, got: {results}")

        # The invariant: balance must never be negative
        final_balance = get_available_balance(merchant)
        self.assertGreaterEqual(
            final_balance, 0,
            f"Balance went negative: {final_balance} paise"
        )

        # Exactly one payout should have been created
        payout_count = Payout.objects.filter(merchant=merchant).count()
        self.assertEqual(payout_count, 1, f"Expected 1 payout, got {payout_count}")

    def test_concurrent_payouts_both_affordable(self):
        """
        When both requests are individually affordable, both should succeed.
        Merchant has 20,000 paise, two requests for 7,000 paise each.
        """
        merchant, bank_account = create_merchant_with_balance(20_000)
        results = []

        def submit_payout():
            client = Client()
            resp = client.post(
                '/api/v1/payouts/',
                data={'amount_paise': 7_000, 'bank_account_id': str(bank_account.id)},
                content_type='application/json',
                HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
                HTTP_X_MERCHANT_ID=str(merchant.id),
            )
            results.append(resp.status_code)

        t1 = threading.Thread(target=submit_payout)
        t2 = threading.Thread(target=submit_payout)
        t1.start(); t2.start()
        t1.join(); t2.join()

        self.assertEqual(results.count(201), 2, f"Both should succeed: {results}")
        final_balance = get_available_balance(merchant)
        self.assertEqual(final_balance, 6_000)  # 20000 - 7000 - 7000
