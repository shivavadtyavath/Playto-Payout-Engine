import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('merchants', '0001_initial'),
        ('payouts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LedgerEntry',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('merchant', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='ledger_entries',
                    to='merchants.merchant',
                )),
                ('entry_type', models.CharField(
                    choices=[('credit', 'Credit'), ('debit', 'Debit')],
                    max_length=6,
                )),
                ('amount_paise', models.BigIntegerField()),
                ('description', models.TextField(blank=True)),
                ('payout', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='ledger_entries',
                    to='payouts.payout',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'ledger_entries'},
        ),
        migrations.AddIndex(
            model_name='ledgerentry',
            index=models.Index(fields=['merchant', 'created_at'], name='ledger_merchant_time_idx'),
        ),
        migrations.AddIndex(
            model_name='ledgerentry',
            index=models.Index(fields=['merchant', 'entry_type'], name='ledger_merchant_type_idx'),
        ),
    ]
