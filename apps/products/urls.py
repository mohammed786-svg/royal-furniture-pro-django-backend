from django.urls import path

from apps.products.views import (
    BrandDetailView,
    BrandListCreateView,
    CatalogMetaOptionsView,
    ProductDetailView,
    ProductListCreateView,
    ProductOptionsView,
    ReviewDetailView,
    ReviewListCreateView,
    TagDetailView,
    TagListCreateView,
)

urlpatterns = [
    path("product-options/", ProductOptionsView.as_view(), name="product-options"),
    path("meta-options/", CatalogMetaOptionsView.as_view(), name="catalog-meta-options"),
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/<int:product_id>/", ProductDetailView.as_view(), name="product-detail"),
    path("brands/", BrandListCreateView.as_view(), name="brand-list"),
    path("brands/<int:brand_id>/", BrandDetailView.as_view(), name="brand-detail"),
    path("reviews/", ReviewListCreateView.as_view(), name="review-list"),
    path("reviews/<int:review_id>/", ReviewDetailView.as_view(), name="review-detail"),
    path("tags/", TagListCreateView.as_view(), name="tag-list"),
    path("tags/<int:tag_id>/", TagDetailView.as_view(), name="tag-detail"),
]
