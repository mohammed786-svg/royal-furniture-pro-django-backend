from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Direct PostgreSQL in development (bypass PgBouncer optional)
DATABASES["default"]["PORT"] = os.getenv("DB_PORT", "5432")  # noqa: F405

CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
