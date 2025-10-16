#!/bin/sh

# This script is the entrypoint for the I/O-bound Celery worker.
# It applies the eventlet monkey patch before starting the worker.

echo "--- Starting I/O-bound Celery worker (eventlet) ---"

# Apply the monkey patch and start the worker
celery -A whatsappcrm_backend worker -l INFO -P eventlet -c 100 -Q celery
