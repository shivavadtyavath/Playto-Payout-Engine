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
            name='IdempotencyKey',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('merchant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='idempotency_keys',
                    to='merchants.merchant',
                )),
                ('key', models.CharField(max_length=36)),
                ('response_body', models.JSONField()),
                ('status_code', models.PositiveSmallIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'idempotency_keys'},
        ),
        migrations.AddConstraint(
            model_name='idempotencykey',
            constraint=models.UniqueConstraint(
                fields=['merchant', 'key'],
                name='unique_idempotency_key_per_merchant',
            ),
        ),
        migrations.AddIndex(
            model_name='idempotencykey',
            index=models.Index(fields=['merchant', 'key'], name='idempotency_merchant_key_idx'),
        ),
        migrations.AddIndex(
            model_name='idempotencykey',
            index=models.Index(fields=['created_at'], name='idempotency_created_at_idx'),
        ),
    ]
