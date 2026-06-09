"""
Gunicorn — tuned for 8 CPU / 32 GB RAM / 100k+ concurrent users (behind NGINX + PgBouncer).

Workers = (2 * CPU) + 1 = 17 for 8 cores; use gevent/sync per workload.
With PgBouncer transaction pooling, keep CONN_MAX_AGE=0 in Django.
"""
import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000
timeout = 60
graceful_timeout = 30
keepalive = 5
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
capture_output = True

# 32GB RAM guidance: ~17 workers * 2 threads; monitor RSS; scale horizontally with load balancer
raw_env = ["DJANGO_ENV=production"]
