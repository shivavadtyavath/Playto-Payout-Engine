"""
Payout API tests: validation, balance checks, response shape.
"""
import uuid
from unittest.mock import patch
from django.test import TestCase, Client

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from ledger.queries import get_available_balance
from payouts.models import Payout


def make_merchant(balance_paise=50_000):
    merchant = Merchant.objects.create(
        name='API Test Merchant',
        email=f'api-{uuid.uuid4()}@test.com',
    )
    bank_account = BankAccount.objects.create(
        merchant=merchant,
        account_number='9999999999',
        ifsc_code='ICIC0000001',
        account_holder='API Test',
    )
    if balance_paise > 0:
        LedgerEntry.objects.create(
            merchant=merchant,
            entry_type=LedgerEntry.CREDIT,
            amount_paise=balance_paise,
            description='Test opening balance',
        )
    return merchant, bank_account


class PayoutCreationTest(TestCase):

    def setUp(self):
        self.merchant, self.bank_account = make_merchant(50_000)
        self.client = Client()

    def _post(self, amount_paise, bank_account_id=None, key=None):
        return self.client.post(
            '/api/v1/payouts/',
            data={
                'amount_paise': amount_paise,
                'bank_account_id': str(bank_account_id or self.bank_account.id),
            },
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()),
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
        )

    def test_successful_payout_returns_201(self):
        """
        # Feature: playto-payout-engine, Property 9: Payout Response Shape Completeness
        """
        with patch('payouts.tasks.process_payout.delay'):
            resp = self._post(10_000)

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertIn('id', data)
        self.assertIn('amount_paise', data)
        self.assertIn('bank_account_id', data)
        self.assertIn('status', data)
        self.assertIn('created_at', data)
        self.assertEqual(data['amount_paise'], 10_000)
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(str(data['bank_account_id']), str(self.bank_account.id))

    def test_insufficient_funds_returns_422(self):
        """
        # Feature: playto-payout-engine, Property 7: Insufficient Funds Rejection
        """
        resp = self._post(100_000)  # more than 50,000 available
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()['code'], 'INSUFFICIENT_FUNDS')
        self.assertEqual(Payout.objects.count(), 0)
        self.assertEqual(LedgerEntry.objects.filter(entry_type='debit').count(), 0)

    def test_zero_amount_returns_400(self):
        """
        # Feature: playto-payout-engine, Property 8: Non-Positive Amount Rejection
        """
        resp = self._post(0)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Payout.objects.count(), 0)

    def test_negative_amount_returns_400(self):
        resp = self._post(-500)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Payout.objects.count(), 0)

    def test_wrong_bank_account_returns_400(self):
        """
        # Feature: playto-payout-engine, Property 5: Bank Account Ownership Enforcement
        """
        other_merchant = Merchant.objects.create(
            name='Other', email=f'other-{uuid.uuid4()}@test.com'
        )
        other_account = BankAccount.objects.create(
            merchant=other_merchant,
            account_number='0000000000',
            ifsc_code='HDFC0000000',
            account_holder='Other',
        )
        resp = self._post(5_000, bank_account_id=other_account.id)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['code'], 'INVALID_BANK_ACCOUNT')
        self.assertEqual(Payout.objects.count(), 0)

    def test_payout_debit_created_atomically(self):
        """
        # Feature: playto-payout-engine, Property 3: Payout Creation Atomicity
        A debit LedgerEntry must exist for every created Payout.
        """
        with patch('payouts.tasks.process_payout.delay'):
            resp = self._post(10_000)

        self.assertEqual(resp.status_code, 201)
        payout_id = resp.json()['id']
        payout = Payout.objects.get(id=payout_id)

        debit = LedgerEntry.objects.filter(
            merchant=self.merchant,
            entry_type=LedgerEntry.DEBIT,
            payout=payout,
        )
        self.assertEqual(debit.count(), 1)
        self.assertEqual(debit.first().amount_paise, 10_000)

    def test_balance_reduced_after_payout(self):
        """Available balance decreases by the payout amount."""
        initial_balance = get_available_balance(self.merchant)

        with patch('payouts.tasks.process_payout.delay'):
            self._post(10_000)

        new_balance = get_available_balance(self.merchant)
        self.assertEqual(new_balance, initial_balance - 10_000)

    def test_missing_merchant_header_returns_401(self):
        resp = self.client.post(
            '/api/v1/payouts/',
            data={'amount_paise': 5_000, 'bank_account_id': str(self.bank_account.id)},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(resp.status_code, 401)


class BalanceQueryTest(TestCase):
    """
    # Feature: playto-payout-engine, Property 1: Balance Round-Trip Consistency
    """

    def test_balance_equals_credits_minus_debits(self):
        merchant = Merchant.objects.create(
            name='Balance Test', email=f'bal-{uuid.uuid4()}@test.com'
        )
        credits = [100_000, 50_000, 25_000]
        debits = [30_000, 15_000]

        for amount in credits:
            LedgerEntry.objects.create(
                merchant=merchant, entry_type='credit', amount_paise=amount, description='c'
            )
        for amount in debits:
            LedgerEntry.objects.create(
                merchant=merchant, entry_type='debit', amount_paise=amount, description='d'
            )

        expected = sum(credits) - sum(debits)
        actual = get_available_balance(merchant)
        self.assertEqual(actual, expected)

    def test_empty_ledger_balance_is_zero(self):
        merchant = Merchant.objects.create(
            name='Empty', email=f'empty-{uuid.uuid4()}@test.com'
        )
        self.assertEqual(get_available_balance(merchant), 0)
