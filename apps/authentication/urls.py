from django.urls import path

from apps.authentication.views import (
    AdminChangePasswordView,
    AdminLoginView,
    AdminLogoutView,
    AdminMeView,
    AdminRefreshView,
    AdminUpdateProfileView,
)

urlpatterns = [
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
    path("admin/refresh/", AdminRefreshView.as_view(), name="admin-refresh"),
    path("admin/logout/", AdminLogoutView.as_view(), name="admin-logout"),
    path("admin/me/", AdminMeView.as_view(), name="admin-me"),
    path("admin/profile/", AdminUpdateProfileView.as_view(), name="admin-profile"),
    path("admin/change-password/", AdminChangePasswordView.as_view(), name="admin-change-password"),
]
