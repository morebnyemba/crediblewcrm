# whatsappcrm_backend/flows/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from conversations.models import Contact, Message
from meta_integration.tasks import send_whatsapp_message_task
from meta_integration.models import MetaAppConfig

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def resolve_human_intervention_after_timeout(self, contact_id: int, intervention_timestamp_iso: str):
    """
    Checks if a human intervention request has timed out and, if so,
    re-enables the bot for the contact and notifies them.

    Args:
        contact_id: The ID of the contact.
        intervention_timestamp_iso: The ISO 8601 string of the timestamp when intervention was requested.
                                    This is used to prevent race conditions.
    """
    try:
        contact = Contact.objects.get(pk=contact_id)
    except Contact.DoesNotExist:
        logger.warning(f"Contact {contact_id} not found for intervention timeout check. Task aborted.")
        return

    # Proceed only if intervention is still active and requested at the specific time this task was created for.
    # This prevents clearing a newer, separate intervention request.
    if (contact.needs_human_intervention and
            contact.intervention_requested_at and
            contact.intervention_requested_at.isoformat() == intervention_timestamp_iso):

        logger.info(f"Human intervention for contact {contact.id} ({contact.whatsapp_id}) has timed out. Re-enabling bot.")

        # Reset the flag and timestamp
        contact.needs_human_intervention = False
        contact.intervention_requested_at = None
        contact.save(update_fields=['needs_human_intervention', 'intervention_requested_at'])

        # Notify the user that the bot is active again
        try:
            active_config = MetaAppConfig.objects.get_active_config()
            message_text = (
                "It seems our pastoral team is currently unavailable. Your request has been noted, and they will get back to you as soon as possible.\n\n"
                "In the meantime, automated assistance has been re-enabled. You can type 'menu' to see other options."
            )

            message = Message.objects.create(
                contact=contact, app_config=active_config, direction='out',
                message_type='text', content_payload={'body': message_text},
                status='pending_dispatch', timestamp=timezone.now()
            )

            send_whatsapp_message_task.delay(message.id, active_config.id)
            logger.info(f"Queued intervention timeout notification {message.id} for contact {contact.id}.")

        except ObjectDoesNotExist as e:
            logger.error(f"Cannot send intervention timeout notification to contact {contact.id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error notifying contact {contact.id} about intervention timeout: {e}", exc_info=True)

    else:
        logger.info(f"Human intervention for contact {contact.id} was already resolved or a new request was made. Timeout task for timestamp {intervention_timestamp_iso} is ignored.")
