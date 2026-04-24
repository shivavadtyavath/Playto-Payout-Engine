import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playto.settings')

app = Celery('playto')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'process-pending-payouts': {
        'task': 'payouts.tasks.process_pending_payouts',
        'schedule': 10.0,  # every 10 seconds
    },
    'retry-stuck-payouts': {
        'task': 'payouts.tasks.retry_stuck_payouts',
        'schedule': 30.0,  # every 30 seconds
    },
}
