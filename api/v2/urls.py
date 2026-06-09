"""API v2 routing — future version."""
from django.urls import path

from api.v2.views import APIv2RootView

urlpatterns = [
    path("", APIv2RootView.as_view(), name="api-v2-root"),
]
