-- =============================================================================
-- ROYAL FURNITURE PRO — PostgreSQL 16 Production Schema
-- Database: royal_furniture_db (recommended)
-- Schema: royal
-- Backend: Django (raw SQL) | Frontend: Next.js | Pool: PgBouncer | Cache: Redis
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS royal;
SET search_path TO royal, public;

-- =============================================================================
-- EXTENSIONS (run as superuser once per database)
-- =============================================================================
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- fuzzy search on product names
-- CREATE EXTENSION IF NOT EXISTS btree_gin;    -- composite GIN indexes
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- optional guest session UUIDs

-- =============================================================================
-- AUTHENTICATION MODULE
-- =============================================================================

CREATE TABLE royal.roletbl (
    role_id BIGSERIAL PRIMARY KEY,
    role_name TEXT NOT NULL DEFAULT 'NA',
    role_code TEXT NOT NULL DEFAULT 'NA',
    description TEXT DEFAULT 'NA',
    is_system_role BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_roletbl_role_code UNIQUE (role_code)
);

CREATE TABLE royal.permissiontbl (
    permission_id BIGSERIAL PRIMARY KEY,
    permission_code TEXT NOT NULL DEFAULT 'NA',
    permission_name TEXT DEFAULT 'NA',
    module_name TEXT DEFAULT 'NA',
    description TEXT DEFAULT 'NA',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_permissiontbl_code UNIQUE (permission_code)
);

CREATE TABLE royal.role_permissiontbl (
    role_permission_id BIGSERIAL PRIMARY KEY,
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    granted_by BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

CREATE TABLE royal.usertbl (
    user_id BIGSERIAL PRIMARY KEY,
    role_id BIGINT NOT NULL,
    email TEXT DEFAULT 'NA',
    phone TEXT DEFAULT 'NA',
    password_hash TEXT DEFAULT 'NA',
    full_name TEXT DEFAULT 'NA',
    avatar_url TEXT DEFAULT 'NA',
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.customertbl (
    customer_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    guest_token TEXT DEFAULT 'NA',
    email TEXT DEFAULT 'NA',
    phone TEXT DEFAULT 'NA',
    full_name TEXT DEFAULT 'NA',
    is_guest BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.admin_sessiontbl (
    admin_session_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    jwt_token TEXT DEFAULT 'NA',
    refresh_token TEXT DEFAULT 'NA',
    login_time TIMESTAMP DEFAULT NOW(),
    expiry_time TIMESTAMP NOT NULL,
    ip_address TEXT DEFAULT 'NA',
    user_agent TEXT DEFAULT 'NA',
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.login_historytbl (
    login_history_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    customer_id BIGINT,
    login_type TEXT DEFAULT 'NA',
    ip_address TEXT DEFAULT 'NA',
    user_agent TEXT DEFAULT 'NA',
    device_type TEXT DEFAULT 'NA',
    location TEXT DEFAULT 'NA',
    status TEXT DEFAULT 'NA',
    failure_reason TEXT DEFAULT 'NA',
    login_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.otptbl (
    otp_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    customer_id BIGINT,
    phone TEXT DEFAULT 'NA',
    email TEXT DEFAULT 'NA',
    otp_code TEXT DEFAULT 'NA',
    otp_type TEXT DEFAULT 'NA',
    purpose TEXT DEFAULT 'NA',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 5,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.device_logtbl (
    device_log_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    customer_id BIGINT,
    device_id TEXT DEFAULT 'NA',
    device_name TEXT DEFAULT 'NA',
    device_type TEXT DEFAULT 'NA',
    os_name TEXT DEFAULT 'NA',
    browser TEXT DEFAULT 'NA',
    fcm_token TEXT DEFAULT 'NA',
    last_seen_at TIMESTAMP DEFAULT NOW(),
    is_trusted BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- DYNAMIC NAVBAR / CATEGORY MODULE
-- =============================================================================

CREATE TABLE royal.categorytbl (
    category_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'NA',
    slug TEXT NOT NULL DEFAULT 'NA',
    image_url TEXT DEFAULT 'NA',
    icon_url TEXT DEFAULT 'NA',
    banner_url TEXT DEFAULT 'NA',
    seo_title TEXT DEFAULT 'NA',
    seo_description TEXT DEFAULT 'NA',
    seo_keywords TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_categorytbl_slug UNIQUE (slug)
);

CREATE TABLE royal.sub_categorytbl (
    sub_category_id BIGSERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL,
    name TEXT NOT NULL DEFAULT 'NA',
    slug TEXT NOT NULL DEFAULT 'NA',
    image_url TEXT DEFAULT 'NA',
    icon_url TEXT DEFAULT 'NA',
    banner_url TEXT DEFAULT 'NA',
    seo_title TEXT DEFAULT 'NA',
    seo_description TEXT DEFAULT 'NA',
    seo_keywords TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_sub_categorytbl_slug UNIQUE (category_id, slug)
);

CREATE TABLE royal.under_sub_categorytbl (
    under_sub_category_id BIGSERIAL PRIMARY KEY,
    sub_category_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    name TEXT NOT NULL DEFAULT 'NA',
    slug TEXT NOT NULL DEFAULT 'NA',
    image_url TEXT DEFAULT 'NA',
    icon_url TEXT DEFAULT 'NA',
    banner_url TEXT DEFAULT 'NA',
    seo_title TEXT DEFAULT 'NA',
    seo_description TEXT DEFAULT 'NA',
    seo_keywords TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_visible BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_under_sub_categorytbl_slug UNIQUE (sub_category_id, slug)
);

-- =============================================================================
-- PRODUCT MANAGEMENT MODULE
-- =============================================================================

CREATE TABLE royal.brandtbl (
    brand_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'NA',
    slug TEXT NOT NULL DEFAULT 'NA',
    logo_url TEXT DEFAULT 'NA',
    description TEXT DEFAULT 'NA',
    website_url TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_brandtbl_slug UNIQUE (slug)
);

CREATE TABLE royal.producttbl (
    product_id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT,
    category_id BIGINT NOT NULL,
    sub_category_id BIGINT,
    under_sub_category_id BIGINT,
    name TEXT NOT NULL DEFAULT 'NA',
    slug TEXT NOT NULL DEFAULT 'NA',
    sku TEXT NOT NULL DEFAULT 'NA',
    hsn_code TEXT DEFAULT 'NA',
    barcode TEXT DEFAULT 'NA',
    short_description TEXT DEFAULT 'NA',
    long_description TEXT DEFAULT 'NA',
    material TEXT DEFAULT 'NA',
    fabric TEXT DEFAULT 'NA',
    color TEXT DEFAULT 'NA',
    dimensions TEXT DEFAULT 'NA',
    weight DOUBLE PRECISION DEFAULT 0,
    assembly_required BOOLEAN DEFAULT FALSE,
    warranty TEXT DEFAULT 'NA',
    country_of_origin TEXT DEFAULT 'NA',
    base_price DOUBLE PRECISION DEFAULT 0,
    sale_price DOUBLE PRECISION DEFAULT 0,
    mrp DOUBLE PRECISION DEFAULT 0,
    gst_percent DOUBLE PRECISION DEFAULT 0,
    seo_title TEXT DEFAULT 'NA',
    seo_description TEXT DEFAULT 'NA',
    seo_keywords TEXT DEFAULT 'NA',
    is_featured BOOLEAN DEFAULT FALSE,
    is_new_arrival BOOLEAN DEFAULT FALSE,
    is_best_seller BOOLEAN DEFAULT FALSE,
    is_trending BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_producttbl_slug UNIQUE (slug),
    CONSTRAINT uq_producttbl_sku UNIQUE (sku)
);

CREATE TABLE royal.product_varianttbl (
    product_variant_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    variant_name TEXT DEFAULT 'NA',
    sku TEXT NOT NULL DEFAULT 'NA',
    barcode TEXT DEFAULT 'NA',
    color TEXT DEFAULT 'NA',
    fabric TEXT DEFAULT 'NA',
    size TEXT DEFAULT 'NA',
    material TEXT DEFAULT 'NA',
    price DOUBLE PRECISION DEFAULT 0,
    sale_price DOUBLE PRECISION DEFAULT 0,
    mrp DOUBLE PRECISION DEFAULT 0,
    weight DOUBLE PRECISION DEFAULT 0,
    dimensions TEXT DEFAULT 'NA',
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_product_varianttbl_sku UNIQUE (sku)
);

CREATE TABLE royal.product_specificationtbl (
    product_specification_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    spec_group TEXT DEFAULT 'NA',
    spec_key TEXT NOT NULL DEFAULT 'NA',
    spec_value TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.product_featuretbl (
    product_feature_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    feature_title TEXT DEFAULT 'NA',
    feature_description TEXT DEFAULT 'NA',
    icon_url TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.product_tagtbl (
    product_tag_id BIGSERIAL PRIMARY KEY,
    tag_name TEXT NOT NULL DEFAULT 'NA',
    slug TEXT NOT NULL DEFAULT 'NA',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_product_tagtbl_slug UNIQUE (slug)
);

CREATE TABLE royal.product_tag_maptbl (
    product_tag_map_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    product_tag_id BIGINT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_product_tag_map UNIQUE (product_id, product_tag_id)
);

CREATE TABLE royal.product_reviewtbl (
    product_review_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    order_id BIGINT,
    title TEXT DEFAULT 'NA',
    review_text TEXT DEFAULT 'NA',
    rating INTEGER DEFAULT 0,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by BIGINT,
    approved_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.product_ratingtbl (
    product_rating_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    total_reviews INTEGER DEFAULT 0,
    average_rating DOUBLE PRECISION DEFAULT 0,
    rating_1_count INTEGER DEFAULT 0,
    rating_2_count INTEGER DEFAULT 0,
    rating_3_count INTEGER DEFAULT 0,
    rating_4_count INTEGER DEFAULT 0,
    rating_5_count INTEGER DEFAULT 0,
    last_calculated_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_product_ratingtbl_product UNIQUE (product_id)
);

CREATE TABLE royal.product_questiontbl (
    product_question_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    question_text TEXT DEFAULT 'NA',
    is_approved BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.product_answertbl (
    product_answer_id BIGSERIAL PRIMARY KEY,
    product_question_id BIGINT NOT NULL,
    answered_by BIGINT,
    answer_text TEXT DEFAULT 'NA',
    is_admin_answer BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.product_viewtbl (
    product_view_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    ip_address TEXT DEFAULT 'NA',
    user_agent TEXT DEFAULT 'NA',
    referrer_url TEXT DEFAULT 'NA',
    viewed_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.related_producttbl (
    related_product_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    related_product_ref_id BIGINT NOT NULL,
    relation_type TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_related_product UNIQUE (product_id, related_product_ref_id)
);

-- =============================================================================
-- PRODUCT MEDIA MODULE
-- =============================================================================

CREATE TABLE royal.product_imagestbl (
    product_image_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    image_url TEXT NOT NULL DEFAULT 'NA',
    alt_text TEXT DEFAULT 'NA',
    image_type TEXT DEFAULT 'NA',
    is_360 BOOLEAN DEFAULT FALSE,
    is_primary BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.product_videostbl (
    product_video_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    video_url TEXT DEFAULT 'NA',
    thumbnail_url TEXT DEFAULT 'NA',
    title TEXT DEFAULT 'NA',
    video_type TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.product_documenttbl (
    product_document_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    document_url TEXT DEFAULT 'NA',
    document_type TEXT DEFAULT 'NA',
    title TEXT DEFAULT 'NA',
    file_size_kb DOUBLE PRECISION DEFAULT 0,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- INVENTORY MANAGEMENT MODULE
-- =============================================================================

CREATE TABLE royal.warehousetbl (
    warehouse_id BIGSERIAL PRIMARY KEY,
    warehouse_code TEXT NOT NULL DEFAULT 'NA',
    name TEXT NOT NULL DEFAULT 'NA',
    address_line1 TEXT DEFAULT 'NA',
    address_line2 TEXT DEFAULT 'NA',
    city TEXT DEFAULT 'NA',
    state TEXT DEFAULT 'NA',
    pincode TEXT DEFAULT 'NA',
    country TEXT DEFAULT 'NA',
    contact_phone TEXT DEFAULT 'NA',
    contact_email TEXT DEFAULT 'NA',
    is_primary BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_warehousetbl_code UNIQUE (warehouse_code)
);

CREATE TABLE royal.inventorytbl (
    inventory_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    warehouse_id BIGINT NOT NULL,
    available_stock INTEGER DEFAULT 0,
    reserved_stock INTEGER DEFAULT 0,
    sold_stock INTEGER DEFAULT 0,
    damaged_stock INTEGER DEFAULT 0,
    returned_stock INTEGER DEFAULT 0,
    warehouse_stock INTEGER DEFAULT 0,
    reorder_level INTEGER DEFAULT 0,
    last_restocked_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_inventory_product_warehouse UNIQUE (product_id, product_variant_id, warehouse_id)
);

CREATE TABLE royal.inventory_transactiontbl (
    inventory_transaction_id BIGSERIAL PRIMARY KEY,
    inventory_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    warehouse_id BIGINT NOT NULL,
    transaction_type TEXT DEFAULT 'NA',
    quantity INTEGER DEFAULT 0,
    reference_type TEXT DEFAULT 'NA',
    reference_id BIGINT,
    notes TEXT DEFAULT 'NA',
    performed_by BIGINT,
    transaction_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.stock_logtbl (
    stock_log_id BIGSERIAL PRIMARY KEY,
    inventory_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    warehouse_id BIGINT NOT NULL,
    action_type TEXT DEFAULT 'NA',
    quantity_before INTEGER DEFAULT 0,
    quantity_after INTEGER DEFAULT 0,
    quantity_changed INTEGER DEFAULT 0,
    reason TEXT DEFAULT 'NA',
    reference_type TEXT DEFAULT 'NA',
    reference_id BIGINT,
    performed_by BIGINT,
    logged_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.stock_adjustmenttbl (
    stock_adjustment_id BIGSERIAL PRIMARY KEY,
    inventory_id BIGINT NOT NULL,
    warehouse_id BIGINT NOT NULL,
    adjustment_type TEXT DEFAULT 'NA',
    quantity INTEGER DEFAULT 0,
    reason TEXT DEFAULT 'NA',
    approved_by BIGINT,
    status TEXT DEFAULT 'PENDING',
    adjusted_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.stock_transfertbl (
    stock_transfer_id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    from_warehouse_id BIGINT NOT NULL,
    to_warehouse_id BIGINT NOT NULL,
    quantity INTEGER DEFAULT 0,
    status TEXT DEFAULT 'PENDING',
    initiated_by BIGINT,
    completed_at TIMESTAMP,
    notes TEXT DEFAULT 'NA',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- REAL-TIME STOCK LOCKING MODULE
-- =============================================================================

CREATE TABLE royal.stock_reservationtbl (
    stock_reservation_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    warehouse_id BIGINT NOT NULL,
    inventory_id BIGINT NOT NULL,
    quantity INTEGER DEFAULT 1,
    reservation_time TIMESTAMP DEFAULT NOW(),
    expiry_time TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    order_id BIGINT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.stock_waitingtbl (
    stock_waiting_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    quantity INTEGER DEFAULT 1,
    email TEXT DEFAULT 'NA',
    phone TEXT DEFAULT 'NA',
    notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMP,
    status TEXT DEFAULT 'WAITING',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- CUSTOMER MODULE
-- =============================================================================

CREATE TABLE royal.customer_profiletbl (
    customer_profile_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    date_of_birth DATE,
    gender TEXT DEFAULT 'NA',
    profile_image TEXT DEFAULT 'NA',
    preferences JSONB DEFAULT '{}',
    newsletter_subscribed BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_customer_profile_customer UNIQUE (customer_id)
);

CREATE TABLE royal.addresstbl (
    address_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    address_type TEXT DEFAULT 'NA',
    full_name TEXT DEFAULT 'NA',
    phone TEXT DEFAULT 'NA',
    address_line1 TEXT DEFAULT 'NA',
    address_line2 TEXT DEFAULT 'NA',
    landmark TEXT DEFAULT 'NA',
    city TEXT DEFAULT 'NA',
    state TEXT DEFAULT 'NA',
    pincode TEXT DEFAULT 'NA',
    country TEXT DEFAULT 'India',
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.customer_notificationtbl (
    customer_notification_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    title TEXT DEFAULT 'NA',
    message TEXT DEFAULT 'NA',
    notification_type TEXT DEFAULT 'NA',
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.customer_wallettbl (
    customer_wallet_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    balance DOUBLE PRECISION DEFAULT 0,
    currency TEXT DEFAULT 'INR',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_customer_wallet_customer UNIQUE (customer_id)
);

CREATE TABLE royal.wallet_transactiontbl (
    wallet_transaction_id BIGSERIAL PRIMARY KEY,
    customer_wallet_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    transaction_type TEXT DEFAULT 'NA',
    amount DOUBLE PRECISION DEFAULT 0,
    balance_before DOUBLE PRECISION DEFAULT 0,
    balance_after DOUBLE PRECISION DEFAULT 0,
    reference_type TEXT DEFAULT 'NA',
    reference_id BIGINT,
    description TEXT DEFAULT 'NA',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.referraltbl (
    referral_id BIGSERIAL PRIMARY KEY,
    referrer_customer_id BIGINT NOT NULL,
    referred_customer_id BIGINT,
    referral_code TEXT NOT NULL DEFAULT 'NA',
    reward_amount DOUBLE PRECISION DEFAULT 0,
    status TEXT DEFAULT 'PENDING',
    completed_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_referraltbl_code UNIQUE (referral_code)
);

-- =============================================================================
-- WISHLIST MODULE
-- =============================================================================

CREATE TABLE royal.wishlisttbl (
    wishlist_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    is_guest BOOLEAN DEFAULT TRUE,
    synced_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- CART MODULE
-- =============================================================================

CREATE TABLE royal.carttbl (
    cart_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    is_guest BOOLEAN DEFAULT TRUE,
    coupon_id BIGINT,
    subtotal DOUBLE PRECISION DEFAULT 0,
    discount_amount DOUBLE PRECISION DEFAULT 0,
    tax_amount DOUBLE PRECISION DEFAULT 0,
    total_amount DOUBLE PRECISION DEFAULT 0,
    item_count INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP DEFAULT NOW(),
    merged_from_session TEXT DEFAULT 'NA',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.cart_itemtbl (
    cart_item_id BIGSERIAL PRIMARY KEY,
    cart_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    quantity INTEGER DEFAULT 1,
    unit_price DOUBLE PRECISION DEFAULT 0,
    line_total DOUBLE PRECISION DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- ORDER MANAGEMENT MODULE
-- =============================================================================

CREATE TABLE royal.order_statustbl (
    order_status_id BIGSERIAL PRIMARY KEY,
    status_code TEXT NOT NULL DEFAULT 'NA',
    status_name TEXT DEFAULT 'NA',
    description TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_terminal BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_order_statustbl_code UNIQUE (status_code)
);

CREATE TABLE royal.ordertbl (
    order_id BIGSERIAL PRIMARY KEY,
    order_number TEXT NOT NULL DEFAULT 'NA',
    customer_id BIGINT NOT NULL,
    order_status_id BIGINT NOT NULL,
    current_status TEXT DEFAULT 'PENDING',
    subtotal DOUBLE PRECISION DEFAULT 0,
    discount_amount DOUBLE PRECISION DEFAULT 0,
    tax_amount DOUBLE PRECISION DEFAULT 0,
    shipping_amount DOUBLE PRECISION DEFAULT 0,
    total_amount DOUBLE PRECISION DEFAULT 0,
    coupon_id BIGINT,
    coupon_code TEXT DEFAULT 'NA',
    shipping_address_id BIGINT,
    billing_address_id BIGINT,
    payment_method TEXT DEFAULT 'QR',
    notes TEXT DEFAULT 'NA',
    ip_address TEXT DEFAULT 'NA',
    user_agent TEXT DEFAULT 'NA',
    confirmed_at TIMESTAMP,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancel_reason TEXT DEFAULT 'NA',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_ordertbl_order_number UNIQUE (order_number)
);

CREATE TABLE royal.order_itemtbl (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT,
    product_name TEXT DEFAULT 'NA',
    sku TEXT DEFAULT 'NA',
    quantity INTEGER DEFAULT 1,
    unit_price DOUBLE PRECISION DEFAULT 0,
    discount_amount DOUBLE PRECISION DEFAULT 0,
    tax_amount DOUBLE PRECISION DEFAULT 0,
    line_total DOUBLE PRECISION DEFAULT 0,
    hsn_code TEXT DEFAULT 'NA',
    warehouse_id BIGINT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.order_trackingtbl (
    order_tracking_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    status_code TEXT DEFAULT 'NA',
    status_message TEXT DEFAULT 'NA',
    location TEXT DEFAULT 'NA',
    tracked_at TIMESTAMP DEFAULT NOW(),
    is_customer_visible BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.order_notestbl (
    order_note_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    note_text TEXT DEFAULT 'NA',
    note_type TEXT DEFAULT 'NA',
    is_customer_visible BOOLEAN DEFAULT FALSE,
    created_by BIGINT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.order_historytbl (
    order_history_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    from_status TEXT DEFAULT 'NA',
    to_status TEXT DEFAULT 'NA',
    changed_by BIGINT,
    change_reason TEXT DEFAULT 'NA',
    metadata JSONB DEFAULT '{}',
    changed_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- PAYMENT MODULE
-- =============================================================================

CREATE TABLE royal.paymenttbl (
    payment_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    payment_method TEXT DEFAULT 'QR',
    payment_amount DOUBLE PRECISION DEFAULT 0,
    currency TEXT DEFAULT 'INR',
    payment_status TEXT DEFAULT 'PENDING',
    transaction_ref TEXT DEFAULT 'NA',
    paid_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.payment_verificationtbl (
    payment_verification_id BIGSERIAL PRIMARY KEY,
    payment_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    utr_number TEXT NOT NULL DEFAULT 'NA',
    payment_amount DOUBLE PRECISION DEFAULT 0,
    screenshot_url TEXT DEFAULT 'NA',
    verification_status TEXT DEFAULT 'PENDING',
    verified_by BIGINT,
    verification_time TIMESTAMP,
    remarks TEXT DEFAULT 'NA',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- SHIPROCKET MODULE
-- =============================================================================

CREATE TABLE royal.shipmenttbl (
    shipment_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    shiprocket_order_id TEXT DEFAULT 'NA',
    shipment_id_external TEXT DEFAULT 'NA',
    awb_number TEXT DEFAULT 'NA',
    courier_name TEXT DEFAULT 'NA',
    tracking_number TEXT DEFAULT 'NA',
    pickup_status TEXT DEFAULT 'NA',
    delivery_status TEXT DEFAULT 'NA',
    shipping_label_url TEXT DEFAULT 'NA',
    estimated_delivery_date DATE,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    raw_response JSONB DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.shipment_trackingtbl (
    shipment_tracking_id BIGSERIAL PRIMARY KEY,
    shipment_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    status_code TEXT DEFAULT 'NA',
    status_message TEXT DEFAULT 'NA',
    location TEXT DEFAULT 'NA',
    tracked_at TIMESTAMP DEFAULT NOW(),
    source TEXT DEFAULT 'SHIPROCKET',
    raw_payload JSONB DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- COUPON MODULE
-- =============================================================================

CREATE TABLE royal.coupontbl (
    coupon_id BIGSERIAL PRIMARY KEY,
    coupon_code TEXT NOT NULL DEFAULT 'NA',
    coupon_name TEXT DEFAULT 'NA',
    discount_type TEXT DEFAULT 'PERCENTAGE',
    discount_value DOUBLE PRECISION DEFAULT 0,
    max_discount_amount DOUBLE PRECISION DEFAULT 0,
    minimum_order_amount DOUBLE PRECISION DEFAULT 0,
    usage_limit INTEGER DEFAULT 0,
    usage_per_customer INTEGER DEFAULT 1,
    used_count INTEGER DEFAULT 0,
    starts_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_coupontbl_code UNIQUE (coupon_code)
);

CREATE TABLE royal.coupon_usagetbl (
    coupon_usage_id BIGSERIAL PRIMARY KEY,
    coupon_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    order_id BIGINT NOT NULL,
    discount_applied DOUBLE PRECISION DEFAULT 0,
    used_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- ANALYTICS MODULE
-- =============================================================================

CREATE TABLE royal.analytics_eventtbl (
    analytics_event_id BIGSERIAL PRIMARY KEY,
    event_type TEXT DEFAULT 'NA',
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    entity_type TEXT DEFAULT 'NA',
    entity_id BIGINT,
    event_data JSONB DEFAULT '{}',
    ip_address TEXT DEFAULT 'NA',
    user_agent TEXT DEFAULT 'NA',
    event_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.page_viewtbl (
    page_view_id BIGSERIAL PRIMARY KEY,
    page_url TEXT DEFAULT 'NA',
    page_title TEXT DEFAULT 'NA',
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    category_id BIGINT,
    sub_category_id BIGINT,
    product_id BIGINT,
    referrer TEXT DEFAULT 'NA',
    ip_address TEXT DEFAULT 'NA',
    viewed_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.search_historytbl (
    search_history_id BIGSERIAL PRIMARY KEY,
    search_query TEXT DEFAULT 'NA',
    customer_id BIGINT,
    session_id TEXT DEFAULT 'NA',
    results_count INTEGER DEFAULT 0,
    clicked_product_id BIGINT,
    ip_address TEXT DEFAULT 'NA',
    searched_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- NOTIFICATION MODULE
-- =============================================================================

CREATE TABLE royal.notificationtbl (
    notification_id BIGSERIAL PRIMARY KEY,
    title TEXT DEFAULT 'NA',
    message TEXT DEFAULT 'NA',
    channel TEXT DEFAULT 'NA',
    template_code TEXT DEFAULT 'NA',
    target_type TEXT DEFAULT 'NA',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.notification_logtbl (
    notification_log_id BIGSERIAL PRIMARY KEY,
    notification_id BIGINT,
    customer_id BIGINT,
    user_id BIGINT,
    channel TEXT DEFAULT 'NA',
    recipient TEXT DEFAULT 'NA',
    subject TEXT DEFAULT 'NA',
    body TEXT DEFAULT 'NA',
    status TEXT DEFAULT 'PENDING',
    sent_at TIMESTAMP,
    failure_reason TEXT DEFAULT 'NA',
    metadata JSONB DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- BANNER MANAGEMENT MODULE
-- =============================================================================

CREATE TABLE royal.banner_positiontbl (
    banner_position_id BIGSERIAL PRIMARY KEY,
    position_code TEXT NOT NULL DEFAULT 'NA',
    position_name TEXT DEFAULT 'NA',
    description TEXT DEFAULT 'NA',
    max_banners INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_banner_position_code UNIQUE (position_code)
);

CREATE TABLE royal.bannertbl (
    banner_id BIGSERIAL PRIMARY KEY,
    banner_position_id BIGINT NOT NULL,
    category_id BIGINT,
    title TEXT DEFAULT 'NA',
    subtitle TEXT DEFAULT 'NA',
    image_url TEXT DEFAULT 'NA',
    mobile_image_url TEXT DEFAULT 'NA',
    link_url TEXT DEFAULT 'NA',
    link_type TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    starts_at TIMESTAMP,
    ends_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- CMS MODULE
-- =============================================================================

CREATE TABLE royal.cms_pagetbl (
    cms_page_id BIGSERIAL PRIMARY KEY,
    page_code TEXT NOT NULL DEFAULT 'NA',
    title TEXT DEFAULT 'NA',
    slug TEXT NOT NULL DEFAULT 'NA',
    content TEXT DEFAULT 'NA',
    seo_title TEXT DEFAULT 'NA',
    seo_description TEXT DEFAULT 'NA',
    seo_keywords TEXT DEFAULT 'NA',
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_cms_pagetbl_slug UNIQUE (slug),
    CONSTRAINT uq_cms_pagetbl_code UNIQUE (page_code)
);

CREATE TABLE royal.faqtbl (
    faq_id BIGSERIAL PRIMARY KEY,
    category TEXT DEFAULT 'NA',
    question TEXT DEFAULT 'NA',
    answer TEXT DEFAULT 'NA',
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

CREATE TABLE royal.testimonialtbl (
    testimonial_id BIGSERIAL PRIMARY KEY,
    customer_name TEXT DEFAULT 'NA',
    customer_image TEXT DEFAULT 'NA',
    location TEXT DEFAULT 'NA',
    rating INTEGER DEFAULT 5,
    testimonial_text TEXT DEFAULT 'NA',
    product_id BIGINT,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- AUDIT LOG MODULE
-- =============================================================================

CREATE TABLE royal.audit_logtbl (
    audit_log_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    customer_id BIGINT,
    action_type TEXT DEFAULT 'NA',
    table_name TEXT DEFAULT 'NA',
    record_id BIGINT,
    old_values JSONB DEFAULT '{}',
    new_values JSONB DEFAULT '{}',
    ip_address TEXT DEFAULT 'NA',
    user_agent TEXT DEFAULT 'NA',
    remarks TEXT DEFAULT 'NA',
    logged_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE
);

-- =============================================================================
-- SYSTEM SETTINGS MODULE
-- =============================================================================

CREATE TABLE royal.settingstbl (
    setting_id BIGSERIAL PRIMARY KEY,
    setting_key TEXT NOT NULL DEFAULT 'NA',
    setting_value TEXT DEFAULT 'NA',
    setting_group TEXT DEFAULT 'NA',
    value_type TEXT DEFAULT 'TEXT',
    is_encrypted BOOLEAN DEFAULT FALSE,
    description TEXT DEFAULT 'NA',
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    epoch DOUBLE PRECISION DEFAULT EXTRACT(EPOCH FROM NOW()),
    date DATE DEFAULT CURRENT_DATE,
    CONSTRAINT uq_settingstbl_key UNIQUE (setting_key)
);

-- =============================================================================
-- FOREIGN KEYS
-- =============================================================================

ALTER TABLE royal.role_permissiontbl
    ADD CONSTRAINT fk_role_permission_role FOREIGN KEY (role_id) REFERENCES royal.roletbl(role_id),
    ADD CONSTRAINT fk_role_permission_permission FOREIGN KEY (permission_id) REFERENCES royal.permissiontbl(permission_id),
    ADD CONSTRAINT fk_role_permission_granted_by FOREIGN KEY (granted_by) REFERENCES royal.usertbl(user_id);

ALTER TABLE royal.usertbl
    ADD CONSTRAINT fk_usertbl_role FOREIGN KEY (role_id) REFERENCES royal.roletbl(role_id);

ALTER TABLE royal.customertbl
    ADD CONSTRAINT fk_customertbl_user FOREIGN KEY (user_id) REFERENCES royal.usertbl(user_id);

ALTER TABLE royal.admin_sessiontbl
    ADD CONSTRAINT fk_admin_session_user FOREIGN KEY (user_id) REFERENCES royal.usertbl(user_id);

ALTER TABLE royal.login_historytbl
    ADD CONSTRAINT fk_login_history_user FOREIGN KEY (user_id) REFERENCES royal.usertbl(user_id),
    ADD CONSTRAINT fk_login_history_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.otptbl
    ADD CONSTRAINT fk_otp_user FOREIGN KEY (user_id) REFERENCES royal.usertbl(user_id),
    ADD CONSTRAINT fk_otp_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.device_logtbl
    ADD CONSTRAINT fk_device_log_user FOREIGN KEY (user_id) REFERENCES royal.usertbl(user_id),
    ADD CONSTRAINT fk_device_log_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.sub_categorytbl
    ADD CONSTRAINT fk_sub_category_category FOREIGN KEY (category_id) REFERENCES royal.categorytbl(category_id);

ALTER TABLE royal.under_sub_categorytbl
    ADD CONSTRAINT fk_under_sub_category_sub FOREIGN KEY (sub_category_id) REFERENCES royal.sub_categorytbl(sub_category_id),
    ADD CONSTRAINT fk_under_sub_category_category FOREIGN KEY (category_id) REFERENCES royal.categorytbl(category_id);

ALTER TABLE royal.producttbl
    ADD CONSTRAINT fk_product_brand FOREIGN KEY (brand_id) REFERENCES royal.brandtbl(brand_id),
    ADD CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES royal.categorytbl(category_id),
    ADD CONSTRAINT fk_product_sub_category FOREIGN KEY (sub_category_id) REFERENCES royal.sub_categorytbl(sub_category_id),
    ADD CONSTRAINT fk_product_under_sub_category FOREIGN KEY (under_sub_category_id) REFERENCES royal.under_sub_categorytbl(under_sub_category_id);

ALTER TABLE royal.product_varianttbl
    ADD CONSTRAINT fk_product_variant_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.product_specificationtbl
    ADD CONSTRAINT fk_product_spec_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.product_featuretbl
    ADD CONSTRAINT fk_product_feature_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.product_tag_maptbl
    ADD CONSTRAINT fk_product_tag_map_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_product_tag_map_tag FOREIGN KEY (product_tag_id) REFERENCES royal.product_tagtbl(product_tag_id);

ALTER TABLE royal.product_reviewtbl
    ADD CONSTRAINT fk_product_review_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_product_review_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.product_ratingtbl
    ADD CONSTRAINT fk_product_rating_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.product_questiontbl
    ADD CONSTRAINT fk_product_question_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_product_question_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.product_answertbl
    ADD CONSTRAINT fk_product_answer_question FOREIGN KEY (product_question_id) REFERENCES royal.product_questiontbl(product_question_id),
    ADD CONSTRAINT fk_product_answer_user FOREIGN KEY (answered_by) REFERENCES royal.usertbl(user_id);

ALTER TABLE royal.product_viewtbl
    ADD CONSTRAINT fk_product_view_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_product_view_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.related_producttbl
    ADD CONSTRAINT fk_related_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_related_product_ref FOREIGN KEY (related_product_ref_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.product_imagestbl
    ADD CONSTRAINT fk_product_images_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_product_images_variant FOREIGN KEY (product_variant_id) REFERENCES royal.product_varianttbl(product_variant_id);

ALTER TABLE royal.product_videostbl
    ADD CONSTRAINT fk_product_videos_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.product_documenttbl
    ADD CONSTRAINT fk_product_document_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.inventorytbl
    ADD CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_inventory_variant FOREIGN KEY (product_variant_id) REFERENCES royal.product_varianttbl(product_variant_id),
    ADD CONSTRAINT fk_inventory_warehouse FOREIGN KEY (warehouse_id) REFERENCES royal.warehousetbl(warehouse_id);

ALTER TABLE royal.inventory_transactiontbl
    ADD CONSTRAINT fk_inv_txn_inventory FOREIGN KEY (inventory_id) REFERENCES royal.inventorytbl(inventory_id),
    ADD CONSTRAINT fk_inv_txn_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_inv_txn_warehouse FOREIGN KEY (warehouse_id) REFERENCES royal.warehousetbl(warehouse_id);

ALTER TABLE royal.stock_logtbl
    ADD CONSTRAINT fk_stock_log_inventory FOREIGN KEY (inventory_id) REFERENCES royal.inventorytbl(inventory_id);

ALTER TABLE royal.stock_adjustmenttbl
    ADD CONSTRAINT fk_stock_adj_inventory FOREIGN KEY (inventory_id) REFERENCES royal.inventorytbl(inventory_id),
    ADD CONSTRAINT fk_stock_adj_warehouse FOREIGN KEY (warehouse_id) REFERENCES royal.warehousetbl(warehouse_id);

ALTER TABLE royal.stock_transfertbl
    ADD CONSTRAINT fk_stock_transfer_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_stock_transfer_from FOREIGN KEY (from_warehouse_id) REFERENCES royal.warehousetbl(warehouse_id),
    ADD CONSTRAINT fk_stock_transfer_to FOREIGN KEY (to_warehouse_id) REFERENCES royal.warehousetbl(warehouse_id);

ALTER TABLE royal.stock_reservationtbl
    ADD CONSTRAINT fk_stock_res_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id),
    ADD CONSTRAINT fk_stock_res_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id),
    ADD CONSTRAINT fk_stock_res_warehouse FOREIGN KEY (warehouse_id) REFERENCES royal.warehousetbl(warehouse_id),
    ADD CONSTRAINT fk_stock_res_inventory FOREIGN KEY (inventory_id) REFERENCES royal.inventorytbl(inventory_id);

ALTER TABLE royal.stock_waitingtbl
    ADD CONSTRAINT fk_stock_wait_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id),
    ADD CONSTRAINT fk_stock_wait_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.customer_profiletbl
    ADD CONSTRAINT fk_customer_profile FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.addresstbl
    ADD CONSTRAINT fk_address_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.customer_notificationtbl
    ADD CONSTRAINT fk_cust_notif_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.customer_wallettbl
    ADD CONSTRAINT fk_customer_wallet FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.wallet_transactiontbl
    ADD CONSTRAINT fk_wallet_txn_wallet FOREIGN KEY (customer_wallet_id) REFERENCES royal.customer_wallettbl(customer_wallet_id),
    ADD CONSTRAINT fk_wallet_txn_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.referraltbl
    ADD CONSTRAINT fk_referral_referrer FOREIGN KEY (referrer_customer_id) REFERENCES royal.customertbl(customer_id),
    ADD CONSTRAINT fk_referral_referred FOREIGN KEY (referred_customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.wishlisttbl
    ADD CONSTRAINT fk_wishlist_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id),
    ADD CONSTRAINT fk_wishlist_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.carttbl
    ADD CONSTRAINT fk_cart_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.cart_itemtbl
    ADD CONSTRAINT fk_cart_item_cart FOREIGN KEY (cart_id) REFERENCES royal.carttbl(cart_id),
    ADD CONSTRAINT fk_cart_item_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.ordertbl
    ADD CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id),
    ADD CONSTRAINT fk_order_status FOREIGN KEY (order_status_id) REFERENCES royal.order_statustbl(order_status_id),
    ADD CONSTRAINT fk_order_shipping_address FOREIGN KEY (shipping_address_id) REFERENCES royal.addresstbl(address_id),
    ADD CONSTRAINT fk_order_billing_address FOREIGN KEY (billing_address_id) REFERENCES royal.addresstbl(address_id);

ALTER TABLE royal.order_itemtbl
    ADD CONSTRAINT fk_order_item_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id),
    ADD CONSTRAINT fk_order_item_product FOREIGN KEY (product_id) REFERENCES royal.producttbl(product_id);

ALTER TABLE royal.order_trackingtbl
    ADD CONSTRAINT fk_order_tracking_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

ALTER TABLE royal.order_notestbl
    ADD CONSTRAINT fk_order_note_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

ALTER TABLE royal.order_historytbl
    ADD CONSTRAINT fk_order_history_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

ALTER TABLE royal.paymenttbl
    ADD CONSTRAINT fk_payment_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id),
    ADD CONSTRAINT fk_payment_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id);

ALTER TABLE royal.payment_verificationtbl
    ADD CONSTRAINT fk_payment_ver_payment FOREIGN KEY (payment_id) REFERENCES royal.paymenttbl(payment_id),
    ADD CONSTRAINT fk_payment_ver_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id),
    ADD CONSTRAINT fk_payment_ver_admin FOREIGN KEY (verified_by) REFERENCES royal.usertbl(user_id);

ALTER TABLE royal.shipmenttbl
    ADD CONSTRAINT fk_shipment_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

ALTER TABLE royal.shipment_trackingtbl
    ADD CONSTRAINT fk_shipment_track_shipment FOREIGN KEY (shipment_id) REFERENCES royal.shipmenttbl(shipment_id),
    ADD CONSTRAINT fk_shipment_track_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

ALTER TABLE royal.coupon_usagetbl
    ADD CONSTRAINT fk_coupon_usage_coupon FOREIGN KEY (coupon_id) REFERENCES royal.coupontbl(coupon_id),
    ADD CONSTRAINT fk_coupon_usage_customer FOREIGN KEY (customer_id) REFERENCES royal.customertbl(customer_id),
    ADD CONSTRAINT fk_coupon_usage_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

ALTER TABLE royal.bannertbl
    ADD CONSTRAINT fk_banner_position FOREIGN KEY (banner_position_id) REFERENCES royal.banner_positiontbl(banner_position_id),
    ADD CONSTRAINT fk_banner_category FOREIGN KEY (category_id) REFERENCES royal.categorytbl(category_id);

-- Deferred FKs (circular references)
ALTER TABLE royal.product_reviewtbl
    ADD CONSTRAINT fk_product_review_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

ALTER TABLE royal.carttbl
    ADD CONSTRAINT fk_cart_coupon FOREIGN KEY (coupon_id) REFERENCES royal.coupontbl(coupon_id);

ALTER TABLE royal.ordertbl
    ADD CONSTRAINT fk_order_coupon FOREIGN KEY (coupon_id) REFERENCES royal.coupontbl(coupon_id);

ALTER TABLE royal.stock_reservationtbl
    ADD CONSTRAINT fk_stock_res_order FOREIGN KEY (order_id) REFERENCES royal.ordertbl(order_id);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Authentication
CREATE INDEX idx_usertbl_email ON royal.usertbl(email) WHERE is_deleted = FALSE;
CREATE INDEX idx_usertbl_phone ON royal.usertbl(phone) WHERE is_deleted = FALSE;
CREATE INDEX idx_usertbl_role ON royal.usertbl(role_id);
CREATE INDEX idx_customertbl_user ON royal.customertbl(user_id);
CREATE INDEX idx_customertbl_guest_token ON royal.customertbl(guest_token) WHERE is_guest = TRUE;
CREATE INDEX idx_admin_session_user ON royal.admin_sessiontbl(user_id);
CREATE INDEX idx_admin_session_expiry ON royal.admin_sessiontbl(expiry_time) WHERE is_revoked = FALSE;
CREATE INDEX idx_admin_session_jwt ON royal.admin_sessiontbl(jwt_token);
CREATE INDEX idx_login_history_user ON royal.login_historytbl(user_id, login_at DESC);
CREATE INDEX idx_otp_phone ON royal.otptbl(phone, expires_at) WHERE is_verified = FALSE;
CREATE INDEX idx_device_log_customer ON royal.device_logtbl(customer_id);

-- Categories / Navbar
CREATE INDEX idx_category_display ON royal.categorytbl(display_order) WHERE is_visible = TRUE AND is_deleted = FALSE;
CREATE INDEX idx_sub_category_category ON royal.sub_categorytbl(category_id, display_order);
CREATE INDEX idx_under_sub_category_sub ON royal.under_sub_categorytbl(sub_category_id, display_order);

-- Products
CREATE INDEX idx_product_category ON royal.producttbl(category_id, sub_category_id, under_sub_category_id) WHERE is_active = TRUE AND is_deleted = FALSE;
CREATE INDEX idx_product_brand ON royal.producttbl(brand_id);
CREATE INDEX idx_product_slug ON royal.producttbl(slug);
CREATE INDEX idx_product_featured ON royal.producttbl(is_featured, is_new_arrival, is_best_seller, is_trending) WHERE is_active = TRUE;
CREATE INDEX idx_product_created ON royal.producttbl(created_at DESC);
CREATE INDEX idx_product_variant_product ON royal.product_varianttbl(product_id);
CREATE INDEX idx_product_spec_product ON royal.product_specificationtbl(product_id);
CREATE INDEX idx_product_images_product ON royal.product_imagestbl(product_id, display_order);
CREATE INDEX idx_product_view_product ON royal.product_viewtbl(product_id, viewed_at DESC);
CREATE INDEX idx_product_view_date ON royal.product_viewtbl(date);
CREATE INDEX idx_related_product ON royal.related_producttbl(product_id);

-- Inventory
CREATE INDEX idx_inventory_product_warehouse ON royal.inventorytbl(product_id, warehouse_id);
CREATE INDEX idx_inventory_warehouse ON royal.inventorytbl(warehouse_id);
CREATE INDEX idx_inventory_available ON royal.inventorytbl(available_stock) WHERE is_active = TRUE;
CREATE INDEX idx_inv_txn_inventory ON royal.inventory_transactiontbl(inventory_id, transaction_at DESC);
CREATE INDEX idx_stock_log_inventory ON royal.stock_logtbl(inventory_id, logged_at DESC);
CREATE INDEX idx_stock_reservation_status ON royal.stock_reservationtbl(status, expiry_time) WHERE status = 'ACTIVE';
CREATE INDEX idx_stock_reservation_product ON royal.stock_reservationtbl(product_id, customer_id);
CREATE INDEX idx_stock_waiting_product ON royal.stock_waitingtbl(product_id, status);

-- Customers
CREATE INDEX idx_address_customer ON royal.addresstbl(customer_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_address_default ON royal.addresstbl(customer_id) WHERE is_default = TRUE;
CREATE INDEX idx_customer_notif_unread ON royal.customer_notificationtbl(customer_id) WHERE is_read = FALSE;
CREATE INDEX idx_wallet_txn_customer ON royal.wallet_transactiontbl(customer_id, created_at DESC);

-- Wishlist / Cart
CREATE INDEX idx_wishlist_customer ON royal.wishlisttbl(customer_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_wishlist_session ON royal.wishlisttbl(session_id) WHERE is_guest = TRUE;
CREATE UNIQUE INDEX idx_wishlist_customer_product ON royal.wishlisttbl(customer_id, product_id, COALESCE(product_variant_id, 0)) WHERE customer_id IS NOT NULL AND is_deleted = FALSE;
CREATE INDEX idx_cart_customer ON royal.carttbl(customer_id) WHERE is_active = TRUE;
CREATE INDEX idx_cart_session ON royal.carttbl(session_id) WHERE is_guest = TRUE;
CREATE INDEX idx_cart_item_cart ON royal.cart_itemtbl(cart_id);

-- Orders
CREATE INDEX idx_order_customer ON royal.ordertbl(customer_id, created_at DESC);
CREATE INDEX idx_order_status ON royal.ordertbl(current_status, order_status_id);
CREATE INDEX idx_order_date ON royal.ordertbl(date);
CREATE INDEX idx_order_created ON royal.ordertbl(created_at DESC);
CREATE INDEX idx_order_item_order ON royal.order_itemtbl(order_id);
CREATE INDEX idx_order_history_order ON royal.order_historytbl(order_id, changed_at DESC);
CREATE INDEX idx_order_tracking_order ON royal.order_trackingtbl(order_id, tracked_at DESC);

-- Payments
CREATE INDEX idx_payment_order ON royal.paymenttbl(order_id);
CREATE INDEX idx_payment_status ON royal.paymenttbl(payment_status);
CREATE INDEX idx_payment_ver_utr ON royal.payment_verificationtbl(utr_number);
CREATE INDEX idx_payment_ver_status ON royal.payment_verificationtbl(verification_status);

-- Shipments
CREATE INDEX idx_shipment_order ON royal.shipmenttbl(order_id);
CREATE INDEX idx_shipment_awb ON royal.shipmenttbl(awb_number);
CREATE INDEX idx_shipment_track_shipment ON royal.shipment_trackingtbl(shipment_id, tracked_at DESC);

-- Coupons
CREATE INDEX idx_coupon_code ON royal.coupontbl(coupon_code) WHERE is_active = TRUE;
CREATE INDEX idx_coupon_usage_customer ON royal.coupon_usagetbl(customer_id, coupon_id);

-- Analytics
CREATE INDEX idx_analytics_event_type ON royal.analytics_eventtbl(event_type, event_at DESC);
CREATE INDEX idx_analytics_event_date ON royal.analytics_eventtbl(date);
CREATE INDEX idx_page_view_date ON royal.page_viewtbl(viewed_at DESC);
CREATE INDEX idx_search_history_query ON royal.search_historytbl(search_query, searched_at DESC);

-- Notifications / Banners / CMS / Audit
CREATE INDEX idx_notification_log_customer ON royal.notification_logtbl(customer_id, created_at DESC);
CREATE INDEX idx_banner_position ON royal.bannertbl(banner_position_id, display_order) WHERE is_active = TRUE;
CREATE INDEX idx_cms_page_slug ON royal.cms_pagetbl(slug);
CREATE INDEX idx_audit_log_table ON royal.audit_logtbl(table_name, record_id, logged_at DESC);
CREATE INDEX idx_audit_log_user ON royal.audit_logtbl(user_id, logged_at DESC);
CREATE INDEX idx_settings_group ON royal.settingstbl(setting_group);

-- =============================================================================
-- SEED DATA: ROLES & ORDER STATUSES
-- =============================================================================

INSERT INTO royal.roletbl (role_name, role_code, description, is_system_role) VALUES
    ('Super Admin', 'SUPER_ADMIN', 'Full platform access', TRUE),
    ('Admin Manager', 'ADMIN_MANAGER', 'Operational admin access', TRUE),
    ('Customer', 'CUSTOMER', 'Storefront customer', TRUE)
ON CONFLICT (role_code) DO NOTHING;

INSERT INTO royal.order_statustbl (status_code, status_name, display_order, is_terminal) VALUES
    ('PENDING', 'Pending', 1, FALSE),
    ('PAYMENT_PENDING', 'Payment Pending', 2, FALSE),
    ('PAYMENT_VERIFIED', 'Payment Verified', 3, FALSE),
    ('CONFIRMED', 'Confirmed', 4, FALSE),
    ('PROCESSING', 'Processing', 5, FALSE),
    ('PACKED', 'Packed', 6, FALSE),
    ('SHIPPED', 'Shipped', 7, FALSE),
    ('DELIVERED', 'Delivered', 8, TRUE),
    ('RETURNED', 'Returned', 9, TRUE),
    ('CANCELLED', 'Cancelled', 10, TRUE),
    ('REFUNDED', 'Refunded', 11, TRUE)
ON CONFLICT (status_code) DO NOTHING;

INSERT INTO royal.banner_positiontbl (position_code, position_name) VALUES
    ('HOME_HERO', 'Homepage Hero'),
    ('HOME_OFFER', 'Homepage Offer Strip'),
    ('CATEGORY_TOP', 'Category Page Top'),
    ('CATEGORY_SIDEBAR', 'Category Sidebar')
ON CONFLICT (position_code) DO NOTHING;

-- =============================================================================
-- TRIGGERS: updated_at auto-touch (optional, enable in production)
-- =============================================================================

CREATE OR REPLACE FUNCTION royal.touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.epoch = EXTRACT(EPOCH FROM NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to high-churn tables via:
-- CREATE TRIGGER trg_producttbl_updated BEFORE UPDATE ON royal.producttbl
--     FOR EACH ROW EXECUTE FUNCTION royal.touch_updated_at();

-- =============================================================================
-- PARTITIONING STRATEGY (PostgreSQL 16 — implement when volume thresholds hit)
-- =============================================================================
--
-- | Table                  | Strategy              | Partition Key   | Retention   |
-- |------------------------|-----------------------|-----------------|-------------|
-- | ordertbl               | RANGE monthly         | created_at      | 24+ months  |
-- | order_historytbl       | RANGE monthly         | created_at      | 24 months   |
-- | order_itemtbl          | HASH (8) or RANGE     | order_id/date   | with orders |
-- | product_viewtbl        | RANGE monthly         | date            | 12 months   |
-- | page_viewtbl           | RANGE monthly         | date            | 6 months    |
-- | analytics_eventtbl     | RANGE monthly         | date            | 12 months   |
-- | search_historytbl      | RANGE monthly         | date            | 6 months    |
-- | login_historytbl       | RANGE monthly         | date            | 12 months   |
-- | audit_logtbl           | RANGE monthly         | date            | 36 months   |
-- | inventory_transactiontbl| RANGE monthly        | date            | 24 months   |
-- | notification_logtbl    | RANGE monthly         | date            | 6 months    |
--
-- Example (run during low-traffic window after backup):
--
-- CREATE TABLE royal.ordertbl_partitioned (LIKE royal.ordertbl INCLUDING ALL)
--     PARTITION BY RANGE (created_at);
-- CREATE TABLE royal.ordertbl_2026_06 PARTITION OF royal.ordertbl_partitioned
--     FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
--
-- Use pg_partman extension for automated partition creation and retention drops.
-- Keep hot partition indexes identical to parent; BRIN on created_at for append-only logs.

-- =============================================================================
-- REDIS CACHE KEY RECOMMENDATIONS
-- =============================================================================
--
-- Navbar (TTL 3600s):
--   royal:navbar:tree                          → full category tree JSON
--   royal:category:{slug}                      → single category + children
--
-- Products (TTL 1800s, invalidate on update):
--   royal:product:{slug}                       → PDP payload
--   royal:product:id:{product_id}              → product by ID
--   royal:product:list:{category_slug}:{page}  → PLP cache
--   royal:product:featured                     → homepage featured
--   royal:product:inventory:{product_id}     → available stock snapshot
--
-- Cart / Wishlist (TTL 604800s = 7 days):
--   royal:cart:session:{session_id}            → guest cart
--   royal:cart:customer:{customer_id}          → logged-in cart
--   royal:wishlist:session:{session_id}
--   royal:wishlist:customer:{customer_id}
--
-- Stock locking (TTL 900s = 15 min reservation):
--   royal:stock:lock:{product_id}:{variant_id} → atomic counter / lock token
--   royal:stock:reservation:{reservation_id}
--
-- Auth (TTL matches JWT):
--   royal:admin:session:{user_id}              → admin session meta
--   royal:admin:jwt:blacklist:{jti}            → revoked tokens
--   royal:otp:{phone}:{purpose}                → OTP rate limit + code
--
-- Orders / Payments:
--   royal:order:{order_number}                 → order summary
--   royal:payment:pending:{order_id}
--
-- Settings / CMS (TTL 86400s):
--   royal:settings:all                         → key-value map
--   royal:cms:page:{slug}
--   royal:banners:{position_code}
--
-- Analytics (TTL 300s rolling aggregates):
--   royal:analytics:dashboard:daily:{date}
--   royal:analytics:top_products:{date}
--
-- Rate limiting:
--   royal:ratelimit:ip:{ip}:api
--   royal:ratelimit:login:{phone}

-- =============================================================================
-- PGBOUNCER RECOMMENDATIONS (transaction pooling for Django raw SQL)
-- =============================================================================
--
-- pool_mode = transaction
-- max_client_conn = 10000
-- default_pool_size = 100
-- min_pool_size = 20
-- reserve_pool_size = 25
-- reserve_pool_timeout = 3
-- server_idle_timeout = 600
-- query_timeout = 30
-- server_lifetime = 3600
--
-- Django DATABASES: CONN_MAX_AGE = 0 (let PgBouncer own pooling)
-- Use separate PgBouncer pools:
--   royal_furniture_write → primary (orders, inventory, payments)
--   royal_furniture_read  → replica (PLP, CMS, analytics reads)
--
-- Prepared statements: disable in Django if using transaction pooling
--   OPTIONS: {'options': '-c search_path=royal,public'}

-- =============================================================================
-- DATABASE OPTIMIZATION RECOMMENDATIONS
-- =============================================================================
--
-- 1. Hardware: NVMe SSD, 32GB+ RAM, shared_buffers = 25% RAM, effective_cache_size = 75% RAM
-- 2. Connections: max_connections = 200 on PG; app connections via PgBouncer only
-- 3. WAL: wal_compression = on, archive_mode for PITR backups (pgBackRest)
-- 4. Autovacuum: aggressive on product_viewtbl, analytics_eventtbl, audit_logtbl
-- 5. Read replica: route PLP, navbar, CMS, analytics dashboards to replica
-- 6. Materialized views: refresh nightly
--      royal.mv_product_rating_summary
--      royal.mv_category_product_counts
--      royal.mv_daily_sales_summary
-- 7. Stock updates: use SELECT ... FOR UPDATE on inventorytbl in transactions
-- 8. Buy Now flow:
--      BEGIN → lock inventory row → decrement available, increment reserved
--      → insert stock_reservationtbl → COMMIT → cache lock in Redis
-- 9. Cron: expire stock_reservationtbl WHERE expiry_time < NOW() → release reserved
-- 10. Full-text search: GIN index on producttbl USING gin(to_tsvector('english', name || ' ' || short_description))
-- 11. Monitoring: pg_stat_statements, slow query log > 500ms
-- 12. Security: row-level policies optional for multi-tenant; encrypt settingstbl secrets at app layer

-- =============================================================================
-- TABLE PURPOSE REFERENCE
-- =============================================================================
--
-- AUTHENTICATION
-- roletbl              → RBAC role definitions (SUPER_ADMIN, ADMIN_MANAGER, CUSTOMER)
-- permissiontbl        → Granular permissions per module/action
-- role_permissiontbl   → Many-to-many role ↔ permission mapping
-- usertbl              → All login identities (admin + linked customer accounts)
-- customertbl          → Commerce identity (guest + registered); links to usertbl when registered
-- admin_sessiontbl     → Admin JWT/refresh sessions with 12h expiry tracking
-- login_historytbl     → Security audit trail for all login attempts
-- otptbl               → Phone/email OTP verification with expiry and attempt limits
-- device_logtbl        → Device fingerprinting and push notification tokens
--
-- NAVBAR
-- categorytbl          → Top-level mega menu (Living, Bedroom, etc.)
-- sub_categorytbl      → Second level (Sofas, Beds, Recliners)
-- under_sub_categorytbl→ Third level (Fabric Sofa, King Size Bed)
--
-- PRODUCTS
-- brandtbl             → Manufacturer/brand master
-- producttbl           → Core SKU catalog with SEO and merchandising flags
-- product_varianttbl   → Color/size/fabric variants with own SKU and price
-- product_specificationtbl → Dynamic key-value specs per product
-- product_featuretbl   → Marketing feature bullets
-- product_tagtbl       → Tag dictionary
-- product_tag_maptbl   → Product ↔ tag association
-- product_reviewtbl    → Customer reviews (moderated)
-- product_ratingtbl    → Denormalized aggregate ratings for fast PLP/PDP
-- product_questiontbl  → Q&A questions
-- product_answertbl    → Q&A answers (admin or customer)
-- product_viewtbl      → Product view events for analytics
-- related_producttbl   → Cross-sell / upsell relationships
-- product_imagestbl    → Images including 360 and primary image flag
-- product_videostbl    → Product videos
-- product_documenttbl  → PDFs (catalog, installation guides)
--
-- INVENTORY
-- warehousetbl         → Warehouse locations (multi-warehouse ready)
-- inventorytbl         → Per-SKU per-warehouse stock buckets
-- inventory_transactiontbl → Immutable stock movement ledger
-- stock_logtbl         → Detailed before/after stock change log
-- stock_adjustmenttbl  → Manual adjustments with approval workflow
-- stock_transfertbl    → Inter-warehouse transfers
-- stock_reservationtbl → Buy-now / checkout stock holds with expiry
-- stock_waitingtbl     → Back-in-stock notification waitlist
--
-- CUSTOMER
-- customer_profiletbl  → Extended profile (DOB, preferences)
-- addresstbl           → Multiple shipping/billing addresses
-- customer_notificationtbl → In-app notification inbox
-- customer_wallettbl   → Store credit wallet balance
-- wallet_transactiontbl→ Wallet credit/debit ledger
-- referraltbl          → Referral program tracking
--
-- COMMERCE
-- wishlisttbl          → Guest + customer wishlist with sync support
-- carttbl              → Persistent cart header (guest session or customer)
-- cart_itemtbl         → Line items in cart
-- order_statustbl      → Order status lookup / workflow definition
-- ordertbl             → Order header with amounts and addresses
-- order_itemtbl        → Order line items (snapshot at purchase time)
-- order_trackingtbl    → Customer-visible shipment milestones
-- order_notestbl       → Internal and customer order notes
-- order_historytbl     → Status change audit trail
-- paymenttbl           → Payment records per order
-- payment_verificationtbl → QR payment UTR verification workflow
-- shipmenttbl          → Shiprocket shipment master
-- shipment_trackingtbl → Courier tracking events from Shiprocket webhooks
-- coupontbl            → Discount coupon definitions
-- coupon_usagetbl      → Per-customer coupon redemption log
--
-- ANALYTICS & ENGAGEMENT
-- analytics_eventtbl   → Generic event stream (clicks, conversions)
-- page_viewtbl         → Page-level traffic analytics
-- search_historytbl    → Search queries for merchandising insights
-- notificationtbl      → Notification templates
-- notification_logtbl  → Delivery log (email/SMS/WhatsApp/push)
-- banner_positiontbl   → Ad slot definitions
-- bannertbl            → Banner creatives per position
-- cms_pagetbl          → Static pages (About, Privacy, Terms, etc.)
-- faqtbl               → FAQ content
-- testimonialtbl       → Customer testimonials for homepage
-- audit_logtbl         → Admin/system audit (INSERT/UPDATE/DELETE/LOGIN/PAYMENT)
-- settingstbl          → Key-value system config (GST, credentials, QR, etc.)
