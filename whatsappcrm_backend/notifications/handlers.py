# whatsappcrm_backend/notifications/handlers.py

import logging
from django.dispatch import receiver
from meta_integration.signals import message_send_failed
from .services import queue_notifications_to_users

logger = logging.getLogger(__name__)

@receiver(message_send_failed)
def handle_failed_message_notification(sender, message_instance, **kwargs):
    """
    Listens for the message_send_failed signal and queues a notification
    to the admin team.
    """
    try:
        contact = message_instance.contact
        logger.info(
            f"Signal received: Message send failed for contact '{contact.name}' ({contact.whatsapp_id}). "
            f"Queuing admin notification."
        )

        message_body = (
            f"🚨 Message Sending Failure 🚨\n\n"
            f"A message to *{contact.name or contact.whatsapp_id}* failed to send after multiple retries.\n\n"
            f"Please check the conversation history and Celery logs for details.\n"
            f"Message ID: {message_instance.id}"
        )
                    # Notify the technical admin team
        queue_notifications_to_users(
            group_names=["Technical Admin"],
            message_body=message_body,
            related_contact=contact
        )
    except Exception as e:
        logger.critical(
            f"CRITICAL: Failed to queue notification for failed message {message_instance.id}. Error: {e}",
            exc_info=True
        )