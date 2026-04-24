from django.urls import path
from .views import MerchantMeView, BankAccountListView

urlpatterns = [
    path('merchants/me/', MerchantMeView.as_view(), name='merchant-me'),
    path('merchants/me/bank-accounts/', BankAccountListView.as_view(), name='bank-account-list'),
]
