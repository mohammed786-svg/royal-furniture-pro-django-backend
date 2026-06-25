from django.urls import path

from apps.marketing.views import (
    BannerDetailView,
    BannerListCreateView,
    BannerPositionListView,
    CmsPageDetailView,
    CmsPageListCreateView,
    CouponDetailView,
    CouponListCreateView,
    FaqDetailView,
    FaqListCreateView,
    HeroBannersView,
    MarketingMetaOptionsView,
    TestimonialDetailView,
    TestimonialListCreateView,
)

urlpatterns = [
    path("meta-options/", MarketingMetaOptionsView.as_view(), name="marketing-meta-options"),
    path("hero-banners/", HeroBannersView.as_view(), name="marketing-hero-banners"),
    path("coupons/", CouponListCreateView.as_view(), name="coupon-list"),
    path("coupons/<int:coupon_id>/", CouponDetailView.as_view(), name="coupon-detail"),
    path("banners/", BannerListCreateView.as_view(), name="banner-list"),
    path("banners/<int:banner_id>/", BannerDetailView.as_view(), name="banner-detail"),
    path("banner-positions/", BannerPositionListView.as_view(), name="banner-position-list"),
    path("cms-pages/", CmsPageListCreateView.as_view(), name="cms-page-list"),
    path("cms-pages/<int:cms_page_id>/", CmsPageDetailView.as_view(), name="cms-page-detail"),
    path("testimonials/", TestimonialListCreateView.as_view(), name="testimonial-list"),
    path("testimonials/<int:testimonial_id>/", TestimonialDetailView.as_view(), name="testimonial-detail"),
    path("faqs/", FaqListCreateView.as_view(), name="faq-list"),
    path("faqs/<int:faq_id>/", FaqDetailView.as_view(), name="faq-detail"),
]
