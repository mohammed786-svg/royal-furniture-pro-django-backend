from django.urls import path

from apps.audit_logs.views import AuditLogDetailView, AuditLogListCreateView

urlpatterns = [
    path("", AuditLogListCreateView.as_view(), name="audit-log-list"),
    path("<int:audit_log_id>/", AuditLogDetailView.as_view(), name="audit-log-detail"),
]
