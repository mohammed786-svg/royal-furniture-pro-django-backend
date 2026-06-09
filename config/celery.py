"""Celery application configuration."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("royal_furniture_pro")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(
    [
        "core.tasks.notifications",
        "core.tasks.inventory",
        "core.tasks.orders",
    ],
    related_name="tasks",
)
