# whatsappcrm_backend/flows/signals.py
import logging
from django.dispatch import receiver

from django.db import close_old_connections
from meta_integration.signals import message_send_failed
from .services import _clear_contact_flow_state

logger = logging.getLogger(__name__)

@receiver(message_send_failed)
def handle_message_send_failure(sender, **kwargs):
    message_instance = kwargs.get('message_instance')
    try:
        if not message_instance or not message_instance.contact:
            return
            
        logger.info(
            f"Flows app received message_send_failed signal for message {message_instance.id} "
            f"to contact {message_instance.contact.id}. Clearing flow state."
        )
        _clear_contact_flow_state(message_instance.contact, error=True)
    finally:
        # Ensure DB connection is closed, as signals can be triggered in long-running processes.
        close_old_connections()