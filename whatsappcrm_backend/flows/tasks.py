# whatsappcrm_backend/flows/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
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

@shared_task(queue='celery') # Use your main I/O queue
def process_flow_for_message_task(message_id: int):
    """
    This task asynchronously runs the entire flow engine for an incoming message.
    """
    # --- FIX for Circular Import ---
    # Import locally to break the import cycle with flows.services.
    from .services import process_message_for_flow
    try:
        with transaction.atomic():
            # Use select_for_update to lock the message row during processing
            # to prevent race conditions if the task is somehow triggered twice.
            # --- FIX for "FOR UPDATE cannot be applied..." error ---
            # First, lock the specific row.
            Message.objects.select_for_update().get(pk=message_id)
            # Then, fetch the object with its related fields.
            incoming_message = Message.objects.select_related('contact', 'app_config').get(pk=message_id)

            # --- Idempotency Check ---
            # If the message has already been processed by the flow engine, log it and exit.
            if incoming_message.flow_processed_at:
                logger.info(f"Skipping flow processing for message {message_id} as it was already processed at {incoming_message.flow_processed_at}.")
                return

            contact = incoming_message.contact
            message_data = incoming_message.content_payload or {}

            actions_to_perform = process_message_for_flow(contact, message_data, incoming_message)

            if not actions_to_perform:
                logger.info(f"Flow processing for message {message_id} resulted in no actions.")
                # Mark as processed even if no actions, to prevent reprocessing.
                incoming_message.flow_processed_at = timezone.now()
                incoming_message.save(update_fields=['flow_processed_at'])
                return

            config_to_use = incoming_message.app_config
            if not config_to_use:
                logger.warning(f"Message {message_id} has no associated app_config. Falling back to active config.")
                config_to_use = MetaAppConfig.objects.get_active_config()

            dispatch_countdown = 0
            for action in actions_to_perform:
                if action.get('type') == 'send_whatsapp_message':
                    recipient_wa_id = action.get('recipient_wa_id', contact.whatsapp_id)
                    
                    recipient_contact, _ = Contact.objects.get_or_create(whatsapp_id=recipient_wa_id)

                    outgoing_msg = Message.objects.create(
                        contact=recipient_contact, app_config=config_to_use, direction='out',
                        message_type=action.get('message_type'), content_payload=action.get('data'),
                        status='pending_dispatch', related_incoming_message=incoming_message
                    )
                    send_whatsapp_message_task.apply_async(args=[outgoing_msg.id, config_to_use.id], countdown=dispatch_countdown)
                    dispatch_countdown += 2
            
            # --- Mark as Processed ---
            # After all actions are dispatched, mark the message as processed.
            incoming_message.flow_processed_at = timezone.now()
            incoming_message.save(update_fields=['flow_processed_at'])

    except Message.DoesNotExist:
        logger.error(f"process_flow_for_message_task: Message with ID {message_id} not found.")
    except Exception as e:
        logger.error(f"Critical error in process_flow_for_message_task for message {message_id}: {e}", exc_info=True)
