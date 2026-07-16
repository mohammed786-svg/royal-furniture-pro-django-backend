from django.urls import path

from apps.settings_app.views import (
    CheckoutPaymentSettingsView,
    SettingDetailView,
    SettingGroupsView,
    SettingListCreateView,
)

urlpatterns = [
    path(
        "checkout-payment/",
        CheckoutPaymentSettingsView.as_view(),
        name="checkout-payment-settings",
    ),
    path("groups/", SettingGroupsView.as_view(), name="setting-groups"),
    path("", SettingListCreateView.as_view(), name="setting-list"),
    path("<int:setting_id>/", SettingDetailView.as_view(), name="setting-detail"),
]
