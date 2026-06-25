"""API v1 routing — register app URLs when implementing endpoints."""
from django.urls import include, path

from api.v1.views import APIv1RootView

urlpatterns = [
    path("", APIv1RootView.as_view(), name="api-v1-root"),
    path("auth/", include("apps.authentication.urls")),
    path("catalog/", include("apps.categories.urls")),
    path("catalog/", include("apps.products.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("marketing/", include("apps.marketing.urls")),
    path("orders/", include("apps.orders.urls")),
    path("customers/", include("apps.customers.urls")),
    path("payments/", include("apps.payments.urls")),
    path("shipping/", include("apps.shiprocket.urls")),
    path("administration/", include("apps.authentication.admin_urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("settings/", include("apps.settings_app.urls")),
    path("audit-logs/", include("apps.audit_logs.urls")),
    path("storefront/", include("apps.storefront.urls")),
]
