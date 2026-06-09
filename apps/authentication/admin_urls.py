from django.urls import path

from apps.authentication.admin_views import (
    AdministrationMetaOptionsView,
    AdminUserDetailView,
    AdminUserListCreateView,
    LoginHistoryDetailView,
    LoginHistoryListView,
)

urlpatterns = [
    path("users/", AdminUserListCreateView.as_view(), name="admin-user-list"),
    path("users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("login-history/", LoginHistoryListView.as_view(), name="login-history-list"),
    path(
        "login-history/<int:login_history_id>/",
        LoginHistoryDetailView.as_view(),
        name="login-history-detail",
    ),
    path("meta-options/", AdministrationMetaOptionsView.as_view(), name="administration-meta-options"),
]
