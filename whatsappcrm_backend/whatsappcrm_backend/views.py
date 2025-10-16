# whatsappcrm_backend/whatsappcrm_backend/views.py
from django.http import JsonResponse
from django.db import connection
from django.db.utils import OperationalError

from .celery import app as celery_app

try:
    from django_redis import get_redis_connection
    from redis.exceptions import ConnectionError as RedisConnectionError
    redis_import_ok = True
except ImportError:
    redis_import_ok = False

def health_check(request):
    """
    A detailed health check endpoint.
    Verifies connectivity to the database, Redis, and Celery workers.
    Returns a 200 status code if the app is running, and a 503 if critical
    services are down.
    """
    db_ok = False
    redis_ok = False
    celery_ok = False

    # 1. Check Database connection
    try:
        connection.ensure_connection()
        db_ok = True
    except OperationalError:
        pass  # db_ok remains False

    # 2. Check Redis connection (if django_redis is installed)
    if redis_import_ok:
        try:
            redis_conn = get_redis_connection("default")
            redis_conn.ping()
            redis_ok = True
        except RedisConnectionError:
            pass  # redis_ok remains False

    # 3. Check Celery workers
    try:
        # Ping workers with a short timeout
        workers = celery_app.control.ping(timeout=0.5)
        if workers:
            celery_ok = True
    except Exception:
        pass  # celery_ok remains False

    all_ok = db_ok and redis_ok and celery_ok
    status_code = 200 if all_ok else 503

    return JsonResponse({
        "status": "ok" if all_ok else "error",
        "services": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
            "celery": "ok" if celery_ok else "error",
        }
    }, status=status_code)