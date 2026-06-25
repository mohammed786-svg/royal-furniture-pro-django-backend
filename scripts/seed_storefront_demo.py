#!/usr/bin/env python
"""
Seed Royal Furniture Pro storefront demo data (Royal Oak–inspired catalog).

Usage:
  cd django_backend && source .venv/bin/activate
  python scripts/seed_storefront_demo.py
  python scripts/seed_storefront_demo.py --force
  python scripts/seed_storefront_demo.py --skip-images
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import django
from django.contrib.auth.hashers import make_password

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from core.cache.cache_keys import CacheKeys  # noqa: E402
from core.cache.cache_manager import cache_manager  # noqa: E402
from core.database import execute, insert_query_returning, select_one  # noqa: E402
from scripts.seed_data.catalog import (  # noqa: E402
    BRANDS,
    CATEGORIES,
    COUPONS,
    FAQS,
    FEATURE_SETTINGS,
    HERO_BANNERS,
    PRODUCTS,
    PROMO_BANNERS,
    SEED_PRODUCT_SLUG_PREFIX,
    TESTIMONIALS,
)
from scripts.seed_data.media import download_image, prefetch_images  # noqa: E402

SCHEMA = "royal"
DEMO_CUSTOMER_EMAIL = "customer@royal.com"
DEMO_CUSTOMER_PASSWORD = "royal@2026"
CATEGORY_SLUGS = [c["slug"] for c in CATEGORIES]


def is_seeded() -> bool:
    row = select_one(
        f"SELECT product_id FROM {SCHEMA}.producttbl WHERE slug LIKE %s LIMIT 1",
        [f"{SEED_PRODUCT_SLUG_PREFIX}%"],
    )
    return row is not None


def clear_demo_data() -> None:
    print("Clearing previous demo seed data...")
    product_ids_sql = f"""
        SELECT product_id FROM {SCHEMA}.producttbl WHERE slug LIKE '{SEED_PRODUCT_SLUG_PREFIX}%'
    """
    execute(
        f"DELETE FROM {SCHEMA}.coupon_usagetbl WHERE order_id IN "
        f"(SELECT order_id FROM {SCHEMA}.ordertbl WHERE order_number LIKE 'RFP-DEMO-%')"
    )
    execute(
        f"DELETE FROM {SCHEMA}.order_itemtbl WHERE order_id IN "
        f"(SELECT order_id FROM {SCHEMA}.ordertbl WHERE order_number LIKE 'RFP-DEMO-%')"
    )
    execute(
        f"DELETE FROM {SCHEMA}.order_historytbl WHERE order_id IN "
        f"(SELECT order_id FROM {SCHEMA}.ordertbl WHERE order_number LIKE 'RFP-DEMO-%')"
    )
    execute(f"DELETE FROM {SCHEMA}.ordertbl WHERE order_number LIKE 'RFP-DEMO-%'")
    execute(
        f"DELETE FROM {SCHEMA}.wishlisttbl WHERE product_id IN ({product_ids_sql})"
    )
    execute(
        f"DELETE FROM {SCHEMA}.product_reviewtbl WHERE product_id IN ({product_ids_sql})"
    )
    execute(
        f"DELETE FROM {SCHEMA}.product_ratingtbl WHERE product_id IN ({product_ids_sql})"
    )
    execute(
        f"DELETE FROM {SCHEMA}.product_featuretbl WHERE product_id IN ({product_ids_sql})"
    )
    execute(
        f"DELETE FROM {SCHEMA}.product_specificationtbl WHERE product_id IN ({product_ids_sql})"
    )
    execute(
        f"DELETE FROM {SCHEMA}.product_imagestbl WHERE product_id IN ({product_ids_sql})"
    )
    execute(
        f"DELETE FROM {SCHEMA}.inventorytbl WHERE product_id IN ({product_ids_sql})"
    )
    execute(f"DELETE FROM {SCHEMA}.producttbl WHERE slug LIKE '{SEED_PRODUCT_SLUG_PREFIX}%'")
    execute(
        f"DELETE FROM {SCHEMA}.testimonialtbl WHERE customer_name IN "
        f"('Priya Sharma', 'Rahul Mehta', 'Ananya Reddy')"
    )
    execute(f"DELETE FROM {SCHEMA}.bannertbl WHERE banner_position_id IN "
            f"(SELECT banner_position_id FROM {SCHEMA}.banner_positiontbl "
            f"WHERE position_code IN ('HOME_HERO', 'HOME_PROMO', 'HOME_OFFER'))")
    execute(f"DELETE FROM {SCHEMA}.faqtbl WHERE category IN ('Orders', 'Delivery', 'Returns', 'Payment')")
    execute(f"DELETE FROM {SCHEMA}.coupontbl WHERE coupon_code IN ('ROYAL10', 'FLAT2000')")
    execute(f"DELETE FROM {SCHEMA}.settingstbl WHERE setting_group = 'homepage'")
    execute(f"DELETE FROM {SCHEMA}.cms_pagetbl WHERE page_code = 'HOME_SEO'")
    execute(
        f"DELETE FROM {SCHEMA}.under_sub_categorytbl WHERE category_id IN "
        f"(SELECT category_id FROM {SCHEMA}.categorytbl WHERE slug = ANY(%s))",
        [CATEGORY_SLUGS],
    )
    execute(
        f"DELETE FROM {SCHEMA}.sub_categorytbl WHERE category_id IN "
        f"(SELECT category_id FROM {SCHEMA}.categorytbl WHERE slug = ANY(%s))",
        [CATEGORY_SLUGS],
    )
    execute(f"DELETE FROM {SCHEMA}.categorytbl WHERE slug = ANY(%s)", [CATEGORY_SLUGS])
    execute(
        f"DELETE FROM {SCHEMA}.brandtbl WHERE slug IN ('royal-furniture-pro', 'italian-living', 'malaysian-wood')"
    )
    execute(f"DELETE FROM {SCHEMA}.warehousetbl WHERE warehouse_code = 'RFP-BLR-01'")


def ensure_banner_positions() -> None:
    positions = [
        ("HOME_HERO", "Homepage Hero"),
        ("HOME_PROMO", "Homepage Promo Strip"),
        ("HOME_OFFER", "Homepage Offer Strip"),
        ("CATEGORY_TOP", "Category Page Top"),
        ("CATEGORY_SIDEBAR", "Category Sidebar"),
    ]
    for code, name in positions:
        execute(
            f"""
            INSERT INTO {SCHEMA}.banner_positiontbl (position_code, position_name)
            VALUES (%s, %s)
            ON CONFLICT (position_code) DO NOTHING
            """,
            [code, name],
        )


def get_banner_position_id(code: str) -> int:
    row = select_one(
        f"SELECT banner_position_id FROM {SCHEMA}.banner_positiontbl WHERE position_code = %s",
        [code],
    )
    if not row:
        raise RuntimeError(f"Banner position {code} missing — run royal_furniture.sql first.")
    return int(row["banner_position_id"])


def get_role_id(role_code: str) -> int:
    row = select_one(
        f"SELECT role_id FROM {SCHEMA}.roletbl WHERE role_code = %s AND is_deleted = FALSE",
        [role_code],
    )
    if not row:
        raise RuntimeError(f"Role {role_code} not found.")
    return int(row["role_id"])


def get_order_status_id(code: str) -> int:
    row = select_one(
        f"SELECT order_status_id FROM {SCHEMA}.order_statustbl WHERE status_code = %s",
        [code],
    )
    if not row:
        raise RuntimeError(f"Order status {code} not found.")
    return int(row["order_status_id"])


def seed_brands(*, skip_images: bool) -> dict[str, int]:
    print("Seeding brands...")
    ids: dict[str, int] = {}
    for brand in BRANDS:
        image_url = download_image(brand["image"], subdir="products", skip_download=skip_images)
        row = insert_query_returning(
            f"""
            INSERT INTO {SCHEMA}.brandtbl
                (name, slug, logo_url, description, website_url, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                logo_url = EXCLUDED.logo_url,
                description = EXCLUDED.description,
                updated_at = NOW()
            RETURNING brand_id
            """,
            [
                brand["name"],
                brand["slug"],
                image_url,
                brand["description"],
                "https://www.royaloakindia.com/",
                len(ids) + 1,
            ],
        )
        ids[brand["slug"]] = int(row["brand_id"])
    return ids


def seed_categories(*, skip_images: bool) -> dict[str, Any]:
    print("Seeding categories, sub-categories & navbar tree...")
    maps: dict[str, Any] = {
        "category": {},
        "sub": {},
        "under": {},
    }
    for cat in CATEGORIES:
        image_url = download_image(cat["image"], subdir="categories", skip_download=skip_images)
        cat_row = insert_query_returning(
            f"""
            INSERT INTO {SCHEMA}.categorytbl
                (name, slug, image_url, icon_url, display_order, is_visible, is_featured, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE, %s, TRUE)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                image_url = EXCLUDED.image_url,
                icon_url = EXCLUDED.icon_url,
                display_order = EXCLUDED.display_order,
                is_featured = EXCLUDED.is_featured,
                updated_at = NOW()
            RETURNING category_id
            """,
            [
                cat["name"],
                cat["slug"],
                image_url,
                image_url,
                cat["order"],
                cat.get("featured", False),
            ],
        )
        category_id = int(cat_row["category_id"])
        maps["category"][cat["slug"]] = category_id

        for sub_order, sub in enumerate(cat.get("subs", []), start=1):
            sub_image = download_image(sub["image"], subdir="categories", skip_download=skip_images)
            sub_row = insert_query_returning(
                f"""
                INSERT INTO {SCHEMA}.sub_categorytbl
                    (category_id, name, slug, image_url, icon_url, display_order, is_visible, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE, TRUE)
                ON CONFLICT (category_id, slug) DO UPDATE SET
                    name = EXCLUDED.name,
                    image_url = EXCLUDED.image_url,
                    updated_at = NOW()
                RETURNING sub_category_id
                """,
                [category_id, sub["name"], sub["slug"], sub_image, sub_image, sub_order],
            )
            sub_id = int(sub_row["sub_category_id"])
            maps["sub"][f"{cat['slug']}:{sub['slug']}"] = sub_id

            for under_order, (under_name, under_slug) in enumerate(sub.get("unders", []), start=1):
                under_row = insert_query_returning(
                    f"""
                    INSERT INTO {SCHEMA}.under_sub_categorytbl
                        (sub_category_id, category_id, name, slug, image_url, display_order, is_visible, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE, TRUE)
                    ON CONFLICT (sub_category_id, slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        updated_at = NOW()
                    RETURNING under_sub_category_id
                    """,
                    [sub_id, category_id, under_name, under_slug, sub_image, under_order],
                )
                maps["under"][f"{cat['slug']}:{sub['slug']}:{under_slug}"] = int(
                    under_row["under_sub_category_id"]
                )
    return maps


def seed_products(
    *,
    brand_ids: dict[str, int],
    cat_maps: dict[str, Any],
    skip_images: bool,
) -> list[int]:
    print("Seeding products, images, specs, ratings & inventory...")
    product_ids: list[int] = []
    warehouse_id = seed_warehouse()

    for index, product in enumerate(PRODUCTS, start=1):
        slug = f"{SEED_PRODUCT_SLUG_PREFIX}{product['slug']}"
        sku = f"RFP-{index:04d}"
        category_id = cat_maps["category"][product["category"]]
        sub_key = f"{product['category']}:{product['sub']}"
        sub_id = cat_maps["sub"].get(sub_key)
        under_id = None
        if product.get("under"):
            under_key = f"{product['category']}:{product['sub']}:{product['under']}"
            under_id = cat_maps["under"].get(under_key)

        image_url = download_image(product["image"], subdir="products", skip_download=skip_images)
        sale = float(product["sale"])
        mrp = float(product["mrp"])

        row = insert_query_returning(
            f"""
            INSERT INTO {SCHEMA}.producttbl
                (brand_id, category_id, sub_category_id, under_sub_category_id,
                 name, slug, sku, short_description, long_description,
                 material, base_price, sale_price, mrp, gst_percent,
                 is_featured, is_new_arrival, is_best_seller, is_trending, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 18,
                    %s, %s, %s, %s, TRUE)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                sale_price = EXCLUDED.sale_price,
                mrp = EXCLUDED.mrp,
                is_featured = EXCLUDED.is_featured,
                is_new_arrival = EXCLUDED.is_new_arrival,
                is_best_seller = EXCLUDED.is_best_seller,
                is_trending = EXCLUDED.is_trending,
                updated_at = NOW()
            RETURNING product_id
            """,
            [
                brand_ids.get(product["brand"]),
                category_id,
                sub_id,
                under_id,
                product["name"],
                slug,
                sku,
                f"Premium {product['name']} — inspired by international furniture collections.",
                (
                    f"{product['name']} brings comfort, durability and style to your home. "
                    "Crafted with quality materials and backed by Royal Furniture Pro warranty."
                ),
                "Engineered Wood / Solid Wood",
                sale,
                sale,
                mrp,
                bool(product.get("featured")),
                bool(product.get("new_arrival")),
                bool(product.get("best_seller")),
                bool(product.get("trending")),
            ],
        )
        product_id = int(row["product_id"])
        product_ids.append(product_id)

        execute(
            f"DELETE FROM {SCHEMA}.product_imagestbl WHERE product_id = %s",
            [product_id],
        )
        execute(
            f"""
            INSERT INTO {SCHEMA}.product_imagestbl
                (product_id, image_url, alt_text, image_type, is_primary, display_order, is_active)
            VALUES (%s, %s, %s, 'PRIMARY', TRUE, 1, TRUE)
            """,
            [product_id, image_url, product["name"]],
        )

        execute(
            f"DELETE FROM {SCHEMA}.product_specificationtbl WHERE product_id = %s",
            [product_id],
        )
        specs = [
            ("General", "Brand", product["brand"].replace("-", " ").title()),
            ("General", "Warranty", "12 Months"),
            ("Dimensions", "Assembly", "Carpenter assembly available"),
            ("Delivery", "Timeline", "7–14 business days"),
        ]
        for order, (group, key, value) in enumerate(specs, start=1):
            execute(
                f"""
                INSERT INTO {SCHEMA}.product_specificationtbl
                    (product_id, spec_group, spec_key, spec_value, display_order, is_active)
                VALUES (%s, %s, %s, %s, %s, TRUE)
                """,
                [product_id, group, key, value, order],
            )

        execute(
            f"DELETE FROM {SCHEMA}.product_featuretbl WHERE product_id = %s",
            [product_id],
        )
        features = [
            "Premium finish with long-lasting build quality",
            "Designed for Indian homes and climates",
            "Easy maintenance and wipe-clean surfaces",
        ]
        for order, feat in enumerate(features, start=1):
            execute(
                f"""
                INSERT INTO {SCHEMA}.product_featuretbl
                    (product_id, feature_title, feature_description, display_order, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                """,
                [product_id, feat, feat, order],
            )

        execute(
            f"""
            INSERT INTO {SCHEMA}.product_ratingtbl
                (product_id, total_reviews, average_rating, rating_5_count, rating_4_count)
            VALUES (%s, 12, 4.6, 9, 2)
            ON CONFLICT (product_id) DO UPDATE SET
                total_reviews = EXCLUDED.total_reviews,
                average_rating = EXCLUDED.average_rating,
                updated_at = NOW()
            """,
            [product_id],
        )

        execute(
            f"DELETE FROM {SCHEMA}.inventorytbl WHERE product_id = %s AND warehouse_id = %s",
            [product_id, warehouse_id],
        )
        execute(
            f"""
            INSERT INTO {SCHEMA}.inventorytbl
                (product_id, warehouse_id, available_stock, warehouse_stock, reorder_level, is_active)
            VALUES (%s, %s, 25, 25, 5, TRUE)
            """,
            [product_id, warehouse_id],
        )

    return product_ids


def seed_warehouse() -> int:
    row = insert_query_returning(
        f"""
        INSERT INTO {SCHEMA}.warehousetbl
            (warehouse_code, name, address_line1, city, state, pincode, country,
             contact_phone, contact_email, is_primary, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, 'India', %s, %s, TRUE, TRUE)
        ON CONFLICT (warehouse_code) DO UPDATE SET
            name = EXCLUDED.name,
            updated_at = NOW()
        RETURNING warehouse_id
        """,
        [
            "RFP-BLR-01",
            "Royal Furniture Pro — Bengaluru Hub",
            "Plot 12, Furniture Park, Hosur Road",
            "Bengaluru",
            "Karnataka",
            "560100",
            "+91 80 4000 1234",
            "warehouse@royalfurniturepro.com",
        ],
    )
    return int(row["warehouse_id"])


def seed_banners(*, skip_images: bool) -> None:
    print("Seeding homepage banners...")
    hero_pos = get_banner_position_id("HOME_HERO")
    promo_pos = get_banner_position_id("HOME_PROMO")
    offer_pos = get_banner_position_id("HOME_OFFER")

    execute(f"DELETE FROM {SCHEMA}.bannertbl WHERE banner_position_id IN (%s, %s, %s)", [
        hero_pos, promo_pos, offer_pos,
    ])

    for banner in HERO_BANNERS:
        image_url = download_image(banner["image"], subdir="banners", skip_download=skip_images)
        execute(
            f"""
            INSERT INTO {SCHEMA}.bannertbl
                (banner_position_id, title, subtitle, image_url, mobile_image_url,
                 link_url, link_type, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 'INTERNAL', %s, TRUE)
            """,
            [
                hero_pos,
                banner["title"],
                banner["subtitle"],
                image_url,
                image_url,
                banner["link"],
                banner["order"],
            ],
        )

    for banner in PROMO_BANNERS:
        image_url = download_image(banner["image"], subdir="banners", skip_download=skip_images)
        execute(
            f"""
            INSERT INTO {SCHEMA}.bannertbl
                (banner_position_id, title, subtitle, image_url, mobile_image_url,
                 link_url, link_type, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 'INTERNAL', %s, TRUE)
            """,
            [
                promo_pos,
                banner["title"],
                banner["subtitle"],
                image_url,
                image_url,
                banner["link"],
                banner["order"],
            ],
        )

    offer_image = download_image("banner-offer", subdir="banners", skip_download=skip_images)
    execute(
        f"""
        INSERT INTO {SCHEMA}.bannertbl
            (banner_position_id, title, subtitle, image_url, mobile_image_url,
             link_url, link_type, display_order, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, 'INTERNAL', 1, TRUE)
        """,
        [
            offer_pos,
            "LIMITED TIME DEAL",
            "Flat 70% OFF — No Cost EMI on credit cards",
            offer_image,
            offer_image,
            "/living",
        ],
    )


def seed_homepage_settings(*, skip_images: bool) -> None:
    print("Seeding homepage settings & CMS...")
    feature_paths = prefetch_images(
        list({f["image"] for f in FEATURE_SETTINGS}),
        subdir="categories",
        skip_download=skip_images,
    )
    for index, feature in enumerate(FEATURE_SETTINGS, start=1):
        payload = json.dumps({
            "label": feature["label"],
            "imageUrl": feature_paths[feature["image"]],
        })
        execute(
            f"""
            INSERT INTO {SCHEMA}.settingstbl
                (setting_key, setting_value, setting_group, value_type, description, is_active)
            VALUES (%s, %s, 'homepage', 'JSON', %s, TRUE)
            ON CONFLICT (setting_key) DO UPDATE SET
                setting_value = EXCLUDED.setting_value,
                updated_at = NOW()
            """,
            [f"feature.{index}", payload, feature["label"]],
        )

    offer_payload = json.dumps({
        "headline": "LIMITED TIME DEAL",
        "subheadline": "Flat 70% OFF",
        "ctaLabel": "Shop Now",
        "ctaHref": "/living",
    })
    execute(
        f"""
        INSERT INTO {SCHEMA}.settingstbl
            (setting_key, setting_value, setting_group, value_type, description, is_active)
        VALUES ('offer_bar', %s, 'homepage', 'JSON', 'Homepage offer strip', TRUE)
        ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value
        """,
        [offer_payload],
    )

    seo_content = """
    <h2>Buy Furniture Online at Royal Furniture Pro</h2>
    <p>Royal Furniture Pro is your one-stop destination for international furniture at unbeatable prices.
    Shop sofas, recliners, beds, dining sets, mattresses, outdoor furniture and home decor — delivered across India.</p>
    <p>Enjoy secure payments, no-cost EMI on select cards, and expert delivery & assembly support.</p>
    """
    execute(
        f"""
        INSERT INTO {SCHEMA}.cms_pagetbl
            (page_code, title, slug, content, seo_title, seo_description, is_published, published_at, is_active)
        VALUES ('HOME_SEO', 'Buy Furniture Online', 'home-seo', %s,
                'Buy Furniture Online | Royal Furniture Pro',
                'Shop home & office furniture online — sofas, beds, dining & decor at best prices in India.',
                TRUE, NOW(), TRUE)
        ON CONFLICT (page_code) DO UPDATE SET
            content = EXCLUDED.content,
            is_published = TRUE,
            updated_at = NOW()
        """,
        [seo_content],
    )


def seed_testimonials(*, skip_images: bool) -> None:
    print("Seeding testimonials...")
    execute(
        f"DELETE FROM {SCHEMA}.testimonialtbl WHERE customer_name IN ('Priya Sharma', 'Rahul Mehta', 'Ananya Reddy')"
    )
    for order, item in enumerate(TESTIMONIALS, start=1):
        image_url = download_image(item["image"], subdir="customers", skip_download=skip_images)
        execute(
            f"""
            INSERT INTO {SCHEMA}.testimonialtbl
                (customer_name, customer_image, location, rating, testimonial_text,
                 is_featured, display_order, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE, %s, TRUE)
            """,
            [item["name"], image_url, item["city"], item["rating"], item["text"], order],
        )


def seed_faqs() -> None:
    print("Seeding FAQs...")
    execute(f"DELETE FROM {SCHEMA}.faqtbl WHERE category IN ('Orders', 'Delivery', 'Returns', 'Payment')")
    for order, faq in enumerate(FAQS, start=1):
        execute(
            f"""
            INSERT INTO {SCHEMA}.faqtbl (category, question, answer, display_order, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
            """,
            [faq["category"], faq["question"], faq["answer"], order],
        )


def seed_coupons() -> None:
    print("Seeding coupons...")
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=365)
    for coupon in COUPONS:
        execute(
            f"""
            INSERT INTO {SCHEMA}.coupontbl
                (coupon_code, coupon_name, discount_type, discount_value,
                 max_discount_amount, minimum_order_amount, usage_limit,
                 starts_at, expires_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1000, %s, %s, TRUE)
            ON CONFLICT (coupon_code) DO UPDATE SET
                discount_value = EXCLUDED.discount_value,
                updated_at = NOW()
            """,
            [
                coupon["code"],
                coupon["name"],
                coupon["discount_type"],
                coupon["discount_value"],
                coupon["max_discount"],
                coupon["min_order"],
                now,
                expires,
            ],
        )


def seed_product_reviews(product_ids: list[int]) -> None:
    print("Seeding product reviews...")
    customer = select_one(
        f"SELECT customer_id FROM {SCHEMA}.customertbl WHERE email = %s AND is_deleted = FALSE",
        [DEMO_CUSTOMER_EMAIL],
    )
    if not customer:
        return
    customer_id = int(customer["customer_id"])
    reviews = [
        (product_ids[0], "Sturdy bed with premium finish", 5),
        (product_ids[0], "Assembly was quick, very happy", 4),
        (product_ids[6], "Comfortable recliner for living room", 5),
        (product_ids[2], "Dining set looks elegant", 5),
        (product_ids[12], "Leather sofa quality is excellent", 4),
        (product_ids[8], "Great value dining table", 5),
    ]
    execute(
        f"DELETE FROM {SCHEMA}.product_reviewtbl WHERE customer_id = %s",
        [customer_id],
    )
    for product_id, text, rating in reviews:
        execute(
            f"""
            INSERT INTO {SCHEMA}.product_reviewtbl
                (product_id, customer_id, review_text, rating,
                 is_verified_purchase, is_approved, approved_at, is_active)
            VALUES (%s, %s, %s, %s, TRUE, TRUE, NOW(), TRUE)
            """,
            [product_id, customer_id, text, rating],
        )


def seed_demo_customer_and_orders(product_ids: list[int]) -> None:
    print("Seeding demo customer, address, wishlist & sample orders...")
    role_id = get_role_id("CUSTOMER")

    user_row = select_one(
        f"SELECT user_id FROM {SCHEMA}.usertbl WHERE email = %s AND is_deleted = FALSE",
        [DEMO_CUSTOMER_EMAIL],
    )
    if user_row:
        user_id = int(user_row["user_id"])
    else:
        user_row = insert_query_returning(
            f"""
            INSERT INTO {SCHEMA}.usertbl
                (role_id, email, phone, password_hash, full_name, email_verified, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE, TRUE)
            RETURNING user_id
            """,
            [
                role_id,
                DEMO_CUSTOMER_EMAIL,
                "9876543210",
                make_password(DEMO_CUSTOMER_PASSWORD),
                "Demo Customer",
            ],
        )
        user_id = int(user_row["user_id"])

    cust_row = select_one(
        f"SELECT customer_id FROM {SCHEMA}.customertbl WHERE email = %s AND is_deleted = FALSE",
        [DEMO_CUSTOMER_EMAIL],
    )
    if cust_row:
        customer_id = int(cust_row["customer_id"])
    else:
        cust_row = insert_query_returning(
            f"""
            INSERT INTO {SCHEMA}.customertbl
                (user_id, email, phone, full_name, is_guest, is_active)
            VALUES (%s, %s, %s, %s, FALSE, TRUE)
            RETURNING customer_id
            """,
            [user_id, DEMO_CUSTOMER_EMAIL, "9876543210", "Demo Customer"],
        )
        customer_id = int(cust_row["customer_id"])

    addr_row = select_one(
        f"SELECT address_id FROM {SCHEMA}.addresstbl WHERE customer_id = %s AND is_deleted = FALSE LIMIT 1",
        [customer_id],
    )
    if addr_row:
        address_id = int(addr_row["address_id"])
    else:
        addr_row = insert_query_returning(
            f"""
            INSERT INTO {SCHEMA}.addresstbl
                (customer_id, address_type, full_name, phone, address_line1, city, state,
                 pincode, country, is_default, is_active)
            VALUES (%s, 'HOME', 'Demo Customer', '9876543210',
                    '42 MG Road, Indiranagar', 'Bengaluru', 'Karnataka', '560038', 'India', TRUE, TRUE)
            RETURNING address_id
            """,
            [customer_id],
        )
        address_id = int(addr_row["address_id"])

    execute(
        f"DELETE FROM {SCHEMA}.wishlisttbl WHERE customer_id = %s",
        [customer_id],
    )
    for product_id in product_ids[:3]:
        execute(
            f"""
            INSERT INTO {SCHEMA}.wishlisttbl
                (customer_id, product_id, is_guest, is_active)
            VALUES (%s, %s, FALSE, TRUE)
            """,
            [customer_id, product_id],
        )

    execute(f"DELETE FROM {SCHEMA}.ordertbl WHERE order_number LIKE 'RFP-DEMO-%'")
    if len(product_ids) < 2:
        return

    delivered_status = get_order_status_id("DELIVERED")
    confirmed_status = get_order_status_id("CONFIRMED")
    sample_orders = [
        ("RFP-DEMO-1001", delivered_status, "DELIVERED", product_ids[0], 1),
        ("RFP-DEMO-1002", confirmed_status, "CONFIRMED", product_ids[1], 2),
    ]
    for order_number, status_id, status_code, product_id, qty in sample_orders:
        prod = select_one(
            f"SELECT name, sku, sale_price FROM {SCHEMA}.producttbl WHERE product_id = %s",
            [product_id],
        )
        unit_price = float(prod["sale_price"])
        subtotal = unit_price * qty
        order_row = insert_query_returning(
            f"""
            INSERT INTO {SCHEMA}.ordertbl
                (order_number, customer_id, order_status_id, current_status,
                 subtotal, total_amount, shipping_address_id, billing_address_id,
                 payment_method, confirmed_at, delivered_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'QR', NOW(), NOW())
            RETURNING order_id
            """,
            [
                order_number,
                customer_id,
                status_id,
                status_code,
                subtotal,
                subtotal,
                address_id,
                address_id,
            ],
        )
        order_id = int(order_row["order_id"])
        execute(
            f"""
            INSERT INTO {SCHEMA}.order_itemtbl
                (order_id, product_id, product_name, sku, quantity, unit_price, line_total)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                order_id,
                product_id,
                prod["name"],
                prod["sku"],
                qty,
                unit_price,
                subtotal,
            ],
        )


def invalidate_caches() -> None:
    print("Invalidating Redis caches...")
    cache_manager.delete(CacheKeys.navbar())
    cache_manager.delete(CacheKeys.storefront_home())
    for code in ("HOME_HERO", "HOME_PROMO", "HOME_OFFER"):
        cache_manager.delete(CacheKeys.banners(code))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Royal Furniture Pro demo storefront data")
    parser.add_argument("--force", action="store_true", help="Clear and re-seed demo data")
    parser.add_argument("--skip-images", action="store_true", help="Skip downloading images")
    args = parser.parse_args()

    if is_seeded() and not args.force:
        print("Demo data already exists. Use --force to re-seed.")
        return

    if args.force:
        clear_demo_data()

    ensure_banner_positions()
    brand_ids = seed_brands(skip_images=args.skip_images)
    cat_maps = seed_categories(skip_images=args.skip_images)
    product_ids = seed_products(
        brand_ids=brand_ids,
        cat_maps=cat_maps,
        skip_images=args.skip_images,
    )
    seed_banners(skip_images=args.skip_images)
    seed_homepage_settings(skip_images=args.skip_images)
    seed_testimonials(skip_images=args.skip_images)
    seed_faqs()
    seed_coupons()
    seed_demo_customer_and_orders(product_ids)
    seed_product_reviews(product_ids)
    invalidate_caches()

    print("")
    print("Demo seed complete.")
    print(f"  Products      : {len(product_ids)}")
    print(f"  Categories    : {len(CATEGORIES)}")
    print(f"  Demo customer : {DEMO_CUSTOMER_EMAIL} / {DEMO_CUSTOMER_PASSWORD}")
    print("  Images stored : django_backend/media/")
    print("  Re-run        : python scripts/seed_storefront_demo.py --force")


if __name__ == "__main__":
    main()
