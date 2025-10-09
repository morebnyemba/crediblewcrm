import os
from celery import Celery
import django

from celery.signals import task_prerun, task_postrun
from django.db import close_old_connections
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsappcrm_backend.settings')
django.setup()

# Create the Celery application instance
app = Celery('whatsappcrm_backend')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# ---- TEMPORARY DEBUG PRINT ----
print(f"[DEBUG celery.py] CELERY_BROKER_URL from app.conf: {app.conf.broker_url}")
print(f"[DEBUG celery.py] CELERY_RESULT_BACKEND from app.conf: {app.conf.result_backend}")
# ---- END TEMPORARY DEBUG PRINT ----

# This ensures all task results will be stored in django-db
app.conf.result_backend = 'django-db'
app.conf.result_extended = True  # Store additional task metadata

# Load task modules from all registered Django apps
# We now use the explicit CELERY_IMPORTS setting in settings.py, which is more robust.
# The app.config_from_object call above automatically loads it.
# app.autodiscover_tasks()

# --- Database Connection Management for Celery ---
# This is crucial for preventing 'too many clients' errors with PostgreSQL
# when using persistent worker processes like eventlet/gevent.
@task_prerun.connect
def on_task_prerun(*args, **kwargs):
    """Close old database connections before the task runs."""
    close_old_connections()
    logger.debug("Closed old DB connections before task execution.")

@task_postrun.connect
def on_task_postrun(*args, **kwargs):
    """Close database connections after the task has finished."""
    close_old_connections()
    logger.debug("Closed DB connections after task execution.")
# Test task with result storage
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    return {
        'status': 'success',
        'message': 'Celery is working with django-celery-results!'
    }