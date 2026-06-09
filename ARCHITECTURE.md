# Royal Furniture Pro — Backend Architecture

Enterprise Django foundation using **raw PostgreSQL only** for business data.

## Principles

- **No ORM** for catalog, orders, inventory, payments, etc.
- **Django** for routing, middleware, DRF, Channels, Celery, optional admin
- **Schema:** `royal` (see `database/migrations_sql/royal_furniture.sql`)

## Stack

| Component | Technology |
|-----------|------------|
| Framework | Django 6 + DRF |
| Database | PostgreSQL 16 + raw SQL (`core/database/`) |
| Pooling | PgBouncer (transaction mode) |
| Cache | Redis + `core/cache/` |
| WebSockets | Django Channels + Daphne |
| Tasks | Celery + Celery Beat |
| WSGI | Gunicorn (`deploy/gunicorn/`) |
| Proxy | NGINX (`nginx/`) |

## Project layout

```
config/           # Django project settings (base/dev/staging/prod)
apps/             # Domain apps (routing only, no ORM models)
api/v1, api/v2    # Versioned API roots
core/             # Database, cache, auth, middleware, tasks, websocket
database/         # SQL assets
media/            # Local VPS uploads (NGINX-served)
```

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./scripts/apply_schema.sh
python manage.py migrate --run-syncdb
python manage.py runserver
celery -A config worker -l info
celery -A config beat -l info
daphne -p 8001 config.asgi:application
```

## API (foundation only)

- `GET /health/` — DB + Redis health
- `GET /api/v1/` — version root
- `GET /api/v2/` — reserved

## Next steps

1. Implement repositories per app using `BaseRepository`
2. Add URL includes in `api/v1/urls.py`
3. Wire JWT login to `royal.admin_sessiontbl`
4. Enable Celery Beat schedules for stock reservation expiry
