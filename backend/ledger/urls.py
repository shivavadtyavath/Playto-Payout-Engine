from django.urls import path
from .views import LedgerEntryListView

urlpatterns = [
    path('merchants/me/ledger/', LedgerEntryListView.as_view(), name='ledger-list'),
]
