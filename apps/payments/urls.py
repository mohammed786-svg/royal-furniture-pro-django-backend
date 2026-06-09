from django.urls import path

from apps.payments.views import (
    PaymentDetailView,
    PaymentListCreateView,
    PaymentOptionsView,
    PaymentVerificationDetailView,
    PaymentVerificationListCreateView,
)

urlpatterns = [
    path("meta-options/", PaymentOptionsView.as_view(), name="payment-meta-options"),
    path("payments/", PaymentListCreateView.as_view(), name="payment-list"),
    path("payments/<int:payment_id>/", PaymentDetailView.as_view(), name="payment-detail"),
    path(
        "verifications/",
        PaymentVerificationListCreateView.as_view(),
        name="payment-verification-list",
    ),
    path(
        "verifications/<int:verification_id>/",
        PaymentVerificationDetailView.as_view(),
        name="payment-verification-detail",
    ),
]
