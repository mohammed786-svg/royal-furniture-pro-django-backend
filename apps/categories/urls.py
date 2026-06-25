from django.urls import path

from apps.categories.views import (
    CatalogOptionsView,
    CategoryDetailView,
    CategoryListCreateView,
    NavbarView,
    SubCategoryDetailView,
    SubCategoryListCreateView,
    UnderSubCategoryDetailView,
    UnderSubCategoryListCreateView,
)

urlpatterns = [
    path("navbar/", NavbarView.as_view(), name="catalog-navbar"),
    path("options/", CatalogOptionsView.as_view(), name="catalog-options"),
    path("categories/", CategoryListCreateView.as_view(), name="category-list"),
    path("categories/<int:category_id>/", CategoryDetailView.as_view(), name="category-detail"),
    path("sub-categories/", SubCategoryListCreateView.as_view(), name="sub-category-list"),
    path(
        "sub-categories/<int:sub_category_id>/",
        SubCategoryDetailView.as_view(),
        name="sub-category-detail",
    ),
    path(
        "under-sub-categories/",
        UnderSubCategoryListCreateView.as_view(),
        name="under-sub-category-list",
    ),
    path(
        "under-sub-categories/<int:under_sub_category_id>/",
        UnderSubCategoryDetailView.as_view(),
        name="under-sub-category-detail",
    ),
]
