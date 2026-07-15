"""
Royal Furniture Pro — base Django settings.
Raw PostgreSQL for business data; Django ORM not used for domain models.
"""
from __future__ import annotations

import os
from pathlib import Path

from corsheaders.defaults import default_headers
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Schema
DB_SCHEMA = os.getenv("DB_SCHEMA", "royal")
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "100"))

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "60"))
JWT_REFRESH_TOKEN_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "7"))
ADMIN_SESSION_HOURS = int(os.getenv("ADMIN_SESSION_HOURS", "12"))

# API encryption & debug logging (set DEBUG_API_LOGS=False to silence all API/SQL prints)
API_CRYPTO_KEY = os.getenv("API_CRYPTO_KEY", "")
API_ENCRYPTION_ENABLED = os.getenv("API_ENCRYPTION_ENABLED", "True").lower() == "true"
DEBUG_API_LOGS = os.getenv("DEBUG_API_LOGS", "False").lower() == "true"

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Media / CDN
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
_media_root = os.getenv("MEDIA_ROOT", "media")
MEDIA_ROOT = Path(_media_root) if os.path.isabs(_media_root) else BASE_DIR / _media_root
STATIC_URL = os.getenv("STATIC_URL", "/static/")
STATIC_ROOT = Path(os.getenv("STATIC_ROOT", str(BASE_DIR / "staticfiles")))
CDN_URL = os.getenv("CDN_URL", "").rstrip("/")

# Integrations
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
SHIPROCKET_ENABLED = os.getenv("SHIPROCKET_ENABLED", "True").lower() == "true"
SHIPROCKET_API_BASE_URL = os.getenv("SHIPROCKET_API_BASE_URL", "https://apiv2.shiprocket.in")
SHIPROCKET_EMAIL = os.getenv("SHIPROCKET_EMAIL", "")
SHIPROCKET_PASSWORD = os.getenv("SHIPROCKET_PASSWORD", "")
SHIPROCKET_PICKUP_LOCATION = os.getenv("SHIPROCKET_PICKUP_LOCATION", "Primary")
SHIPROCKET_DEFAULT_WEIGHT_KG = float(os.getenv("SHIPROCKET_DEFAULT_WEIGHT_KG", "1.0"))
SHIPROCKET_DEFAULT_LENGTH_CM = float(os.getenv("SHIPROCKET_DEFAULT_LENGTH_CM", "10"))
SHIPROCKET_DEFAULT_BREADTH_CM = float(os.getenv("SHIPROCKET_DEFAULT_BREADTH_CM", "10"))
SHIPROCKET_DEFAULT_HEIGHT_CM = float(os.getenv("SHIPROCKET_DEFAULT_HEIGHT_CM", "10"))

EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"

SMS_API_KEY = os.getenv("SMS_API_KEY", "")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "apps.authentication",
    "apps.dashboard",
    "apps.categories",
    "apps.products",
    "apps.inventory",
    "apps.marketing",
    "apps.cart",
    "apps.wishlist",
    "apps.orders",
    "apps.payments",
    "apps.shiprocket",
    "apps.customers",
    "apps.notifications",
    "apps.analytics",
    "apps.cms",
    "apps.settings_app",
    "apps.websocket",
    "apps.common",
    "apps.audit_logs",
    "apps.storefront",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.api_encryption.ApiEncryptionMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.request_logging.RequestLoggingMiddleware",
    "core.middleware.rate_limit.RateLimitMiddleware",
    "core.auth.middleware.JWTAuthenticationMiddleware",
    "core.middleware.security_headers.SecurityHeadersMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# PostgreSQL — PgBouncer compatible (transaction pooling)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "royal_furniture_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "6432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "options": f"-c search_path={DB_SCHEMA},public -c timezone=UTC",
        },
    },
}

READ_DB_HOST = os.getenv("READ_DB_HOST", "")
if READ_DB_HOST:
    DATABASES["read"] = {
        **DATABASES["default"],
        "HOST": READ_DB_HOST,
        "PORT": os.getenv("READ_DB_PORT", DATABASES["default"]["PORT"]),
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# Banner / product image uploads (base64 JSON). None = no Django size cap.
DATA_UPLOAD_MAX_MEMORY_SIZE = None
FILE_UPLOAD_MAX_MEMORY_SIZE = None

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "core.exceptions.handlers.custom_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

CORS_ALLOW_HEADERS = (
    *default_headers,
    "x-payload-encrypted",
    "x-guest-session",
)
CORS_EXPOSE_HEADERS = ("x-payload-encrypted", "x-request-id")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
        "json": {
            "format": '{"level":"%(levelname)s","time":"%(asctime)s","logger":"%(name)s","message":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "application_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "application.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "api_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "api.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "database_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "database.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "security.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "websocket_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "websocket.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "payment_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "payment.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "verbose",
        },
        "inventory_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "inventory.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console", "application_file"], "level": "INFO"},
        "api": {"handlers": ["console", "api_file"], "level": "INFO", "propagate": False},
        "database": {"handlers": ["console", "database_file"], "level": "INFO", "propagate": False},
        "security": {"handlers": ["console", "security_file"], "level": "WARNING", "propagate": False},
        "websocket": {"handlers": ["console", "websocket_file"], "level": "INFO", "propagate": False},
        "payment": {"handlers": ["console", "payment_file"], "level": "INFO", "propagate": False},
        "inventory": {"handlers": ["console", "inventory_file"], "level": "INFO", "propagate": False},
        "cache": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "royal.api.debug": {
            "handlers": ["console", "api_file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
