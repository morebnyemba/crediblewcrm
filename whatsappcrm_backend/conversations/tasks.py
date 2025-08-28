# conversations/tasks.py

from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task(name="conversations.tasks.run_fail_stuck_messages_command")
def run_fail_stuck_messages_command():
    """
    Celery task to run the fail_stuck_messages management command periodically.
    """
    logger.info("Executing fail_stuck_messages management command via Celery Beat.")
    try:
        call_command('fail_stuck_messages')
        logger.info("Successfully executed fail_stuck_messages command.")
    except Exception as e:
        logger.error(f"Error executing fail_stuck_messages command: {e}", exc_info=True)