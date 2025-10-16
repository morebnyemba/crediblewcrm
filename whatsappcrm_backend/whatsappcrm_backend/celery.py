import os

# --- FIX for eventlet/prefork pool conflict ---
# Conditionally apply eventlet monkey-patching based on an environment variable.
# This allows you to run different worker types (eventlet for I/O, prefork for CPU)
# from the same codebase without conflicts.
# IMPORTANT: This must run before almost all other imports.
if os.environ.get('CELERY_EXECUTION_POOL') == 'eventlet':
    import eventlet
    eventlet.monkey_patch()

from celery import Celery
import django
import logging
from celery.signals import task_prerun, task_postrun
from celery.signals import worker_process_init, task_prerun, task_postrun
from django.db import close_old_connections
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'whatsappcrm_backend.settings')

logger = logging.getLogger(__name__)
django.setup()

# Create the Celery application instance
app = Celery('whatsappcrm_backend')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
# We now use the explicit CELERY_IMPORTS setting in settings.py, which is more robust.
# The app.config_from_object call above automatically loads it.
# app.autodiscover_tasks()

# --- Database Connection Management for Celery ---
# This is crucial for preventing 'too many clients' errors with PostgreSQL
# when using persistent worker processes like eventlet/gevent.
@worker_process_init.connect
def on_worker_init(**kwargs):
    """Close old database connections when a worker process starts."""
    close_old_connections()
    logger.info("Closed old DB connections at worker process init.")

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