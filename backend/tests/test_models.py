"""
Model integrity tests.

Verifies:
- All monetary fields are BigIntegerField (not Float or Decimal)
- DB constraints work correctly
- Seed data creates expected records
"""
import uuid
from django.test import TestCase
from django.db import IntegrityError

from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry
from payouts.models import Payout
from idempotency.models import IdempotencyKey


class MonetaryFieldTypeTest(TestCase):
    """Verify no FloatField or DecimalField is used for monetary values."""

    def _get_field(self, model, field_name):
        return model._meta.get_field(field_name)

    def test_ledger_entry_amount_is_biginteger(self):
        from django.db.models import BigIntegerField
        field = self._get_field(LedgerEntry, 'amount_paise')
        self.assertIsInstance(field, BigIntegerField,
            "LedgerEntry.amount_paise must be BigIntegerField, not FloatField or DecimalField")

    def test_payout_amount_is_biginteger(self):
        from django.db.models import BigIntegerField
        field = self._get_field(Payout, 'amount_paise')
        self.assertIsInstance(field, BigIntegerField,
            "Payout.amount_paise must be BigIntegerField, not FloatField or DecimalField")

    def test_no_float_fields_in_ledger(self):
        from django.db.models import FloatField, DecimalField
        for field in LedgerEntry._meta.get_fields():
            self.assertNotIsInstance(field, FloatField, f"FloatField found: {field.name}")
            self.assertNotIsInstance(field, DecimalField, f"DecimalField found: {field.name}")

    def test_no_float_fields_in_payout(self):
        from django.db.models import FloatField, DecimalField
        for field in Payout._meta.get_fields():
            self.assertNotIsInstance(field, FloatField, f"FloatField found: {field.name}")
            self.assertNotIsInstance(field, DecimalField, f"DecimalField found: {field.name}")


class IdempotencyConstraintTest(TestCase):
    """Verify the unique constraint on (merchant_id, key) raises IntegrityError on duplicate."""

    def test_duplicate_idempotency_key_raises_integrity_error(self):
        merchant = Merchant.objects.create(
            name='Constraint Test',
            email=f'constraint-{uuid.uuid4()}@test.com',
        )
        key = str(uuid.uuid4())

        IdempotencyKey.objects.create(
            merchant=merchant,
            key=key,
            response_body={'id': 'test'},
            status_code=201,
        )

        with self.assertRaises(IntegrityError):
            IdempotencyKey.objects.create(
                merchant=merchant,
                key=key,
                response_body={'id': 'duplicate'},
                status_code=201,
            )

    def test_same_key_different_merchants_allowed(self):
        """Same key for different merchants should NOT raise IntegrityError."""
        key = str(uuid.uuid4())
        m1 = Merchant.objects.create(name='M1', email=f'm1-{uuid.uuid4()}@test.com')
        m2 = Merchant.objects.create(name='M2', email=f'm2-{uuid.uuid4()}@test.com')

        IdempotencyKey.objects.create(merchant=m1, key=key, response_body={}, status_code=201)
        # Should not raise
        IdempotencyKey.objects.create(merchant=m2, key=key, response_body={}, status_code=201)
        self.assertEqual(IdempotencyKey.objects.filter(key=key).count(), 2)


class SeedDataTest(TestCase):
    """Verify seed data creates expected records."""

    def setUp(self):
        from django.core.management import call_command
        call_command('seed_data', verbosity=0)

    def test_three_merchants_created(self):
        self.assertEqual(Merchant.objects.count(), 3)

    def test_each_merchant_has_bank_account(self):
        for merchant in Merchant.objects.all():
            self.assertGreater(
                merchant.bank_accounts.count(), 0,
                f"Merchant {merchant.name} has no bank accounts"
            )

    def test_each_merchant_has_credits(self):
        for merchant in Merchant.objects.all():
            credit_count = LedgerEntry.objects.filter(
                merchant=merchant,
                entry_type=LedgerEntry.CREDIT,
            ).count()
            self.assertGreaterEqual(credit_count, 2,
                f"Merchant {merchant.name} should have at least 2 credits")

    def test_seed_is_idempotent(self):
        """Running seed_data twice should not create duplicates."""
        from django.core.management import call_command
        call_command('seed_data', verbosity=0)
        self.assertEqual(Merchant.objects.count(), 3)
