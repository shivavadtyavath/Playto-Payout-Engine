"""
Idempotency tests.

Property 10: Idempotency Round-Trip
Feature: playto-payout-engine

Verifies that:
1. Same Idempotency-Key + same merchant → same response, no duplicate payout
2. Same key for different merchants → independent payouts (per-merchant scoping)
3. Missing/invalid key → 400
4. Expired key → new payout created
"""
import uuid
import threading
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, Client
from django.utils.timezone import now

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout
from idempotency.models import IdempotencyKey


def make_merchant(balance_paise=100_000):
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
        description='Opening balance',
    )
    return merchant, bank_account


class IdempotencyRoundTripTest(TestCase):
    """
    # Feature: playto-payout-engine, Property 10: Idempotency Round-Trip
    """

    def setUp(self):
        self.merchant, self.bank_account = make_merchant()
        self.client = Client()

    def _post_payout(self, idempotency_key, amount_paise=5_000):
        return self.client.post(
            '/api/v1/payouts/',
            data={
                'amount_paise': amount_paise,
                'bank_account_id': str(self.bank_account.id),
            },
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=idempotency_key,
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
        )

    def test_duplicate_request_returns_same_response(self):
        """
        # Feature: playto-payout-engine, Property 10: Idempotency Round-Trip
        Same key twice → same status code and response body, only one payout created.
        """
        key = str(uuid.uuid4())

        with patch('payouts.tasks.process_payout.delay'):
            resp1 = self._post_payout(key)
            resp2 = self._post_payout(key)

        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(resp2.status_code, 201)
        self.assertEqual(resp1.json(), resp2.json(), "Responses must be identical")

        payout_count = Payout.objects.filter(merchant=self.merchant).count()
        self.assertEqual(payout_count, 1, "Only one payout should be created")

    def test_different_keys_create_different_payouts(self):
        """Different idempotency keys create independent payouts."""
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        with patch('payouts.tasks.process_payout.delay'):
            resp1 = self._post_payout(key1, amount_paise=5_000)
            resp2 = self._post_payout(key2, amount_paise=5_000)

        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(resp2.status_code, 201)
        self.assertNotEqual(resp1.json()['id'], resp2.json()['id'])
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 2)

    def test_missing_idempotency_key_returns_400(self):
        """Missing Idempotency-Key header → 400."""
        resp = self.client.post(
            '/api/v1/payouts/',
            data={'amount_paise': 5_000, 'bank_account_id': str(self.bank_account.id)},
            content_type='application/json',
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 'INVALID_IDEMPOTENCY_KEY')

    def test_invalid_idempotency_key_returns_400(self):
        """Non-UUID Idempotency-Key header → 400."""
        resp = self.client.post(
            '/api/v1/payouts/',
            data={'amount_paise': 5_000, 'bank_account_id': str(self.bank_account.id)},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='not-a-uuid',
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 'INVALID_IDEMPOTENCY_KEY')

    def test_per_merchant_scoping(self):
        """
        # Feature: playto-payout-engine, Property 11: Per-Merchant Idempotency Scoping
        Same UUID key used by two different merchants → two independent payouts.
        """
        merchant2, bank_account2 = make_merchant()
        shared_key = str(uuid.uuid4())

        with patch('payouts.tasks.process_payout.delay'):
            resp1 = self._post_payout(shared_key, amount_paise=5_000)
            resp2 = self.client.post(
                '/api/v1/payouts/',
                data={'amount_paise': 5_000, 'bank_account_id': str(bank_account2.id)},
                content_type='application/json',
                HTTP_IDEMPOTENCY_KEY=shared_key,
                HTTP_X_MERCHANT_ID=str(merchant2.id),
            )

        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(resp2.status_code, 201)
        self.assertNotEqual(resp1.json()['id'], resp2.json()['id'])
        self.assertEqual(Payout.objects.count(), 2)

    def test_expired_key_allows_new_payout(self):
        """An expired idempotency key (> 24h old) allows a new payout to be created."""
        key = str(uuid.uuid4())

        # Create an expired idempotency key record directly
        IdempotencyKey.objects.create(
            merchant=self.merchant,
            key=key,
            response_body={'id': str(uuid.uuid4()), 'status': 'pending'},
            status_code=201,
            created_at=now() - timedelta(hours=25),  # expired
        )

        with patch('payouts.tasks.process_payout.delay'):
            resp = self._post_payout(key, amount_paise=5_000)

        # Should create a new payout, not return the expired cached response
        self.assertEqual(resp.status_code, 201)

    def test_idempotency_key_stores_complete_record(self):
        """
        # Feature: playto-payout-engine, Property 24: Idempotency Key Stores Complete Record
        After a successful payout, the IdempotencyKey record has all required fields.
        """
        key = str(uuid.uuid4())

        with patch('payouts.tasks.process_payout.delay'):
            self._post_payout(key, amount_paise=5_000)

        record = IdempotencyKey.objects.get(merchant=self.merchant, key=key)
        self.assertIsNotNone(record.merchant_id)
        self.assertEqual(record.key, key)
        self.assertIsNotNone(record.response_body)
        self.assertEqual(record.status_code, 201)
        self.assertIsNotNone(record.created_at)


class ConcurrentIdempotencyTest(TransactionTestCase):
    """
    # Feature: playto-payout-engine, Property 25: Concurrent Duplicate Requests Create Exactly One Payout
    """

    def test_concurrent_same_key_creates_one_payout(self):
        """
        Two concurrent requests with the same Idempotency-Key → exactly one payout.
        The DB unique constraint on (merchant_id, key) is the safety net.
        """
        merchant, bank_account = make_merchant(balance_paise=100_000)
        shared_key = str(uuid.uuid4())
        results = []

        def submit():
            client = Client()
            with patch('payouts.tasks.process_payout.delay'):
                resp = client.post(
                    '/api/v1/payouts/',
                    data={'amount_paise': 5_000, 'bank_account_id': str(bank_account.id)},
                    content_type='application/json',
                    HTTP_IDEMPOTENCY_KEY=shared_key,
                    HTTP_X_MERCHANT_ID=str(merchant.id),
                )
            results.append(resp.status_code)

        t1 = threading.Thread(target=submit)
        t2 = threading.Thread(target=submit)
        t1.start(); t2.start()
        t1.join(); t2.join()

        # Both should return 201 (second gets cached response)
        self.assertTrue(all(s == 201 for s in results), f"Unexpected statuses: {results}")
        # But only one payout should exist
        self.assertEqual(Payout.objects.filter(merchant=merchant).count(), 1)
