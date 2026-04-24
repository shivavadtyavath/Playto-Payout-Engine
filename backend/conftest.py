"""
Pytest configuration.

Sets DJANGO_SETTINGS_MODULE so pytest-django can find the settings.
The concurrency tests use TransactionTestCase which requires a real
PostgreSQL connection — SQLite does not support SELECT FOR UPDATE correctly.
"""
import django
from django.conf import settings


def pytest_configure(config):
    """Called before test collection. Ensures Django is configured."""
    pass
