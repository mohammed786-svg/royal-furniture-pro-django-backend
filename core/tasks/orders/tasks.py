from celery import shared_task


@shared_task(name="orders.ping")
def orders_ping():
    """Placeholder — order background jobs."""
    return "orders worker ready"
