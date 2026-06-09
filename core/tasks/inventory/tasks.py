from celery import shared_task


@shared_task(name="inventory.expire_reservations")
def expire_stock_reservations():
    """Placeholder — expire stock_reservationtbl rows via raw SQL."""
    return "inventory worker ready"
