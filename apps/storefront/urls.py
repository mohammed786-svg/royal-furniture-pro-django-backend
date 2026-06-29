from django.urls import path

from apps.storefront.commerce_views import (
    StorefrontAddressDetailView,
    StorefrontAddressesView,
    StorefrontCartItemDetailView,
    StorefrontCartItemsView,
    StorefrontCartView,
    StorefrontCheckoutView,
    StorefrontGoogleAuthView,
    StorefrontMeView,
    StorefrontSendOtpView,
    StorefrontVerifyOtpView,
    StorefrontWishlistProductView,
    StorefrontWishlistView,
)
from apps.storefront.views import (
    StorefrontCategoryListingView,
    StorefrontHomeView,
    StorefrontProductDetailView,
)

urlpatterns = [
    path("home/", StorefrontHomeView.as_view(), name="storefront-home"),
    path(
        "catalog/<slug:category_slug>/<slug:sub_category_slug>/<slug:under_sub_category_slug>/",
        StorefrontCategoryListingView.as_view(),
        name="storefront-category-listing-under",
    ),
    path(
        "catalog/<slug:category_slug>/<slug:sub_category_slug>/",
        StorefrontCategoryListingView.as_view(),
        name="storefront-category-listing",
    ),
    path(
        "products/<slug:slug>/",
        StorefrontProductDetailView.as_view(),
        name="storefront-product-detail",
    ),
    path("auth/send-otp/", StorefrontSendOtpView.as_view(), name="storefront-send-otp"),
    path("auth/verify-otp/", StorefrontVerifyOtpView.as_view(), name="storefront-verify-otp"),
    path("auth/google/", StorefrontGoogleAuthView.as_view(), name="storefront-google-auth"),
    path("auth/me/", StorefrontMeView.as_view(), name="storefront-me"),
    path("cart/", StorefrontCartView.as_view(), name="storefront-cart"),
    path("cart/items/", StorefrontCartItemsView.as_view(), name="storefront-cart-items"),
    path(
        "cart/items/<int:cart_item_id>/",
        StorefrontCartItemDetailView.as_view(),
        name="storefront-cart-item-detail",
    ),
    path("wishlist/", StorefrontWishlistView.as_view(), name="storefront-wishlist"),
    path(
        "wishlist/<int:product_id>/",
        StorefrontWishlistProductView.as_view(),
        name="storefront-wishlist-product",
    ),
    path("addresses/", StorefrontAddressesView.as_view(), name="storefront-addresses"),
    path(
        "addresses/<int:address_id>/",
        StorefrontAddressDetailView.as_view(),
        name="storefront-address-detail",
    ),
    path("checkout/", StorefrontCheckoutView.as_view(), name="storefront-checkout"),
]
