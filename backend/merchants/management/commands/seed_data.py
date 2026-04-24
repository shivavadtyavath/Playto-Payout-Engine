"""
Seed data management command.

Creates 3 merchants with bank accounts and credit history.
Idempotent: safe to run multiple times (uses get_or_create).

Usage:
    python manage.py seed_data
"""
import uuid
from django.core.management.base import BaseCommand
from merchants.models import Merchant, BankAccount
from ledger.models import LedgerEntry


SEED_MERCHANTS = [
    {
        'id': uuid.UUID('11111111-1111-1111-1111-111111111111'),
        'name': 'Arjun Sharma Design Studio',
        'email': 'arjun@designstudio.in',
        'bank_accounts': [
            {
                'id': uuid.UUID('aaaa1111-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
                'account_number': '1234567890123456',
                'ifsc_code': 'HDFC0001234',
                'account_holder': 'Arjun Sharma',
            }
        ],
        'credits': [
            {'amount_paise': 500000, 'description': 'Payment from Acme Corp (Invoice #001) - $600 USD'},
            {'amount_paise': 350000, 'description': 'Payment from TechStart Inc (Invoice #002) - $420 USD'},
            {'amount_paise': 200000, 'description': 'Payment from GlobalMedia (Invoice #003) - $240 USD'},
        ],
    },
    {
        'id': uuid.UUID('22222222-2222-2222-2222-222222222222'),
        'name': 'Priya Nair Freelance Dev',
        'email': 'priya@freelancedev.in',
        'bank_accounts': [
            {
                'id': uuid.UUID('bbbb2222-bbbb-bbbb-bbbb-bbbbbbbbbbbb'),
                'account_number': '9876543210987654',
                'ifsc_code': 'ICIC0005678',
                'account_holder': 'Priya Nair',
            },
            {
                'id': uuid.UUID('bbbb3333-bbbb-bbbb-bbbb-bbbbbbbbbbbb'),
                'account_number': '1111222233334444',
                'ifsc_code': 'SBIN0009012',
                'account_holder': 'Priya Nair',
            },
        ],
        'credits': [
            {'amount_paise': 750000, 'description': 'Payment from StartupXYZ (Invoice #101) - $900 USD'},
            {'amount_paise': 420000, 'description': 'Payment from DigitalAgency (Invoice #102) - $504 USD'},
        ],
    },
    {
        'id': uuid.UUID('33333333-3333-3333-3333-333333333333'),
        'name': 'Rahul Mehta Content Agency',
        'email': 'rahul@contentagency.in',
        'bank_accounts': [
            {
                'id': uuid.UUID('cccc4444-cccc-cccc-cccc-cccccccccccc'),
                'account_number': '5555666677778888',
                'ifsc_code': 'AXIS0003456',
                'account_holder': 'Rahul Mehta',
            }
        ],
        'credits': [
            {'amount_paise': 300000, 'description': 'Payment from ContentCo (Invoice #201) - $360 USD'},
            {'amount_paise': 180000, 'description': 'Payment from MediaHouse (Invoice #202) - $216 USD'},
            {'amount_paise': 450000, 'description': 'Payment from BrandAgency (Invoice #203) - $540 USD'},
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed the database with test merchants, bank accounts, and credit history.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        for merchant_data in SEED_MERCHANTS:
            merchant, created = Merchant.objects.get_or_create(
                id=merchant_data['id'],
                defaults={
                    'name': merchant_data['name'],
                    'email': merchant_data['email'],
                }
            )
            if created:
                self.stdout.write(f'  Created merchant: {merchant.name}')
            else:
                self.stdout.write(f'  Merchant already exists: {merchant.name}')

            for ba_data in merchant_data['bank_accounts']:
                bank_account, ba_created = BankAccount.objects.get_or_create(
                    id=ba_data['id'],
                    defaults={
                        'merchant': merchant,
                        'account_number': ba_data['account_number'],
                        'ifsc_code': ba_data['ifsc_code'],
                        'account_holder': ba_data['account_holder'],
                    }
                )
                if ba_created:
                    self.stdout.write(f'    Created bank account: {bank_account.account_number}')

            for credit_data in merchant_data['credits']:
                if not LedgerEntry.objects.filter(
                    merchant=merchant,
                    description=credit_data['description'],
                    entry_type=LedgerEntry.CREDIT,
                ).exists():
                    LedgerEntry.objects.create(
                        merchant=merchant,
                        entry_type=LedgerEntry.CREDIT,
                        amount_paise=credit_data['amount_paise'],
                        description=credit_data['description'],
                    )
                    self.stdout.write(
                        f'    Created credit: {credit_data["amount_paise"]} paise'
                    )

        self.stdout.write(self.style.SUCCESS('\nSeed complete!'))
        self.stdout.write('\nMerchant IDs for testing:')
        for m in SEED_MERCHANTS:
            self.stdout.write(f'  {m["name"]}: {m["id"]}')
