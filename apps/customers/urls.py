from django.urls import path

from apps.customers.views import (
    AddressDetailView,
    AddressListCreateView,
    CustomerDetailView,
    CustomerListCreateView,
    CustomerOptionsView,
    WalletDetailView,
    WalletListView,
    WalletTransactionView,
    WishlistDetailView,
    WishlistListView,
)

urlpatterns = [
    path("options/", CustomerOptionsView.as_view(), name="customer-options"),
    path("customers/", CustomerListCreateView.as_view(), name="customer-list"),
    path("customers/<int:customer_id>/", CustomerDetailView.as_view(), name="customer-detail"),
    path("addresses/", AddressListCreateView.as_view(), name="address-list"),
    path("addresses/<int:address_id>/", AddressDetailView.as_view(), name="address-detail"),
    path("wishlists/", WishlistListView.as_view(), name="wishlist-list"),
    path("wishlists/<int:wishlist_id>/", WishlistDetailView.as_view(), name="wishlist-detail"),
    path("wallet/", WalletListView.as_view(), name="wallet-list"),
    path("wallet/<int:customer_wallet_id>/", WalletDetailView.as_view(), name="wallet-detail"),
    path(
        "wallet/<int:customer_wallet_id>/transactions/",
        WalletTransactionView.as_view(),
        name="wallet-transactions",
    ),
]
