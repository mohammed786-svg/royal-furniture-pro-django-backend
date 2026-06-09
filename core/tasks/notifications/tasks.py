from celery import shared_task


@shared_task(name="notifications.ping")
def notifications_ping():
    """Placeholder — implement notification dispatch."""
    return "notifications worker ready"
