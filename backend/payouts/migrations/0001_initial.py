import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('merchants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payout',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('merchant', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='payouts',
                    to='merchants.merchant',
                )),
                ('bank_account', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='payouts',
                    to='merchants.bankaccount',
                )),
                ('amount_paise', models.BigIntegerField()),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('processing', 'Processing'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                    ],
                    default='pending',
                    max_length=12,
                )),
                ('retry_count', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'payouts'},
        ),
        migrations.AddIndex(
            model_name='payout',
            index=models.Index(fields=['merchant', 'status'], name='payout_merchant_status_idx'),
        ),
        migrations.AddIndex(
            model_name='payout',
            index=models.Index(fields=['status', 'updated_at'], name='payout_status_updated_idx'),
        ),
    ]
