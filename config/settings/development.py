from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Remote local UI (laptop :3000 → VPS run_dev.sh) — always allow even if .env lists prod only.
_DEV_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
CORS_ALLOWED_ORIGINS = list(
    dict.fromkeys([*CORS_ALLOWED_ORIGINS, *_DEV_CORS_ORIGINS])  # noqa: F405
)
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Direct PostgreSQL in development (bypass PgBouncer optional)
DATABASES["default"]["PORT"] = os.getenv("DB_PORT", "5432")  # noqa: F405

CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
