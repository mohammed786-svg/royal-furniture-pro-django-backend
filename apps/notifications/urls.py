from django.urls import path

from apps.notifications.views import (
    NotificationDetailView,
    NotificationListCreateView,
    NotificationLogDetailView,
    NotificationLogListView,
    NotificationMetaOptionsView,
)

urlpatterns = [
    path("notifications/", NotificationListCreateView.as_view(), name="notification-list"),
    path(
        "notifications/<int:notification_id>/",
        NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path("notification-logs/", NotificationLogListView.as_view(), name="notification-log-list"),
    path(
        "notification-logs/<int:notification_log_id>/",
        NotificationLogDetailView.as_view(),
        name="notification-log-detail",
    ),
    path("meta-options/", NotificationMetaOptionsView.as_view(), name="notification-meta-options"),
]
