#!/bin/sh

# This script is the entrypoint for the CPU-bound Celery worker.
# It starts a standard 'prefork' worker without any monkey patching.

echo "--- Starting CPU-bound Celery worker (prefork) ---"
celery -A whatsappcrm_backend worker -l INFO -P prefork -c 3 -Q cpu_intensive
