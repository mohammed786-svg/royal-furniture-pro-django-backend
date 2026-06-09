from django.urls import path

from apps.analytics.views import (
    PageViewDashboardView,
    PageViewDetailView,
    PageViewListCreateView,
    SalesDashboardView,
    SearchDashboardView,
    SearchDetailView,
    SearchListCreateView,
)

urlpatterns = [
    path("sales/", SalesDashboardView.as_view(), name="analytics-sales"),
    path("page-views/dashboard/", PageViewDashboardView.as_view(), name="page-view-dashboard"),
    path("page-views/", PageViewListCreateView.as_view(), name="page-view-list"),
    path("page-views/<int:page_view_id>/", PageViewDetailView.as_view(), name="page-view-detail"),
    path("search/dashboard/", SearchDashboardView.as_view(), name="search-dashboard"),
    path("search/", SearchListCreateView.as_view(), name="search-list"),
    path("search/<int:search_history_id>/", SearchDetailView.as_view(), name="search-detail"),
]
