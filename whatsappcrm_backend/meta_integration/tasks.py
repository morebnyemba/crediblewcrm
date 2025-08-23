# whatsappcrm_backend/meta_integration/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from .utils import send_whatsapp_message, send_read_receipt_api
from .models import MetaAppConfig
from conversations.models import Message, Contact # To update message status
from .signals import message_send_failed

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=10, default_retry_delay=10) # bind=True gives access to self, retry settings
def send_whatsapp_message_task(self, outgoing_message_id: int, active_config_id: int):
    """
    Celery task to send a WhatsApp message asynchronously.
    Updates the Message object's status based on the outcome.

    Args:
        outgoing_message_id (int): The ID of the outgoing Message object to send.
        active_config_id (int): The ID of the active MetaAppConfig to use for sending.
    """
    try:
        outgoing_msg = Message.objects.select_related('contact').get(pk=outgoing_message_id)
        active_config = MetaAppConfig.objects.get(pk=active_config_id)
    except Message.DoesNotExist:
        logger.error(f"send_whatsapp_message_task: Message with ID {outgoing_message_id} not found. Task cannot proceed.")
        return # Cannot retry if message doesn't exist
    except MetaAppConfig.DoesNotExist:
        logger.error(f"send_whatsapp_message_task: MetaAppConfig with ID {active_config_id} not found. Task cannot proceed.")
        # Update message status to failed if config is missing
        if 'outgoing_msg' in locals():
            outgoing_msg.status = 'failed'
            outgoing_msg.error_details = {'error': f'MetaAppConfig ID {active_config_id} not found for sending.'}
            outgoing_msg.status_timestamp = timezone.now()
            outgoing_msg.save(update_fields=['status', 'error_details', 'status_timestamp'])
        return

    if outgoing_msg.direction != 'out':
        logger.warning(f"send_whatsapp_message_task: Message ID {outgoing_message_id} is not an outgoing message. Skipping.")
        return

    # Avoid resending if already sent successfully or in a final failed state without retries
    if outgoing_msg.wamid and outgoing_msg.status == 'sent':
        logger.info(f"send_whatsapp_message_task: Message ID {outgoing_message_id} (WAMID: {outgoing_msg.wamid}) already marked as sent. Skipping.")
        return
    if outgoing_msg.status == 'failed' and self.request.retries >= self.max_retries:
         logger.warning(f"send_whatsapp_message_task: Message ID {outgoing_message_id} already failed and max retries reached. Skipping.")
         return

    # Skip sequential delivery check for system notifications
    if outgoing_msg.is_system_notification:
        logger.info(f"Skipping sequential delivery check for system notification message ID {outgoing_message_id}.")
    else:
        # To ensure sequential delivery, check for preceding messages that are either:
        # 1. Still pending dispatch (these should always be sent first).
        # 2. Were sent recently but not yet confirmed as delivered. We'll wait for a short period
        #    (e.g., 2 minutes) for the delivery receipt. This balances sequential delivery with
        #    preventing a single offline user from blocking all future messages indefinitely.
        stale_threshold = timezone.now() - timedelta(minutes=2)

        # Find the specific message causing the halt for better logging
        halting_message = Message.objects.filter(
            Q(contact=outgoing_msg.contact),
            Q(direction='out'),
            Q(id__lt=outgoing_message_id),
            (
                Q(status='pending_dispatch', timestamp__gte=stale_threshold) | # Not yet processed
                Q(status__in=['sent', 'failed'], status_timestamp__gte=stale_threshold) # Processed but not in a final state (sent or awaiting retry)
            )
        ).order_by('-id').first() # Get the most recent one for logging

        if halting_message:
            logger.warning(
                f"send_whatsapp_message_task: Halting message ID {outgoing_message_id} for contact "
                f"{outgoing_msg.contact.whatsapp_id}. Waiting for preceding message ID {halting_message.id} "
                f"(Status: {halting_message.status}, Status Time: {halting_message.status_timestamp}, "
                f"Created: {halting_message.timestamp}). Retrying."
            )
            raise self.retry() # Uses the task's default_retry_delay

    logger.info(f"Task send_whatsapp_message_task started for Message ID: {outgoing_message_id}, Contact: {outgoing_msg.contact.whatsapp_id}")

    try:
        # content_payload should contain the 'data' part for send_whatsapp_message
        # and message_type should be the Meta API message type
        if not isinstance(outgoing_msg.content_payload, dict):
            raise ValueError("Message content_payload is not a valid dictionary for sending.")

        api_response = send_whatsapp_message(
            to_phone_number=outgoing_msg.contact.whatsapp_id,
            message_type=outgoing_msg.message_type, # This should be 'text', 'template', 'interactive'
            data=outgoing_msg.content_payload, # This is the actual data for the type
            config=active_config
        )

        if api_response and api_response.get('messages') and api_response['messages'][0].get('id'):
            outgoing_msg.wamid = api_response['messages'][0]['id']
            outgoing_msg.status = 'sent' # Successfully handed off to Meta
            outgoing_msg.error_details = None # Clear previous errors if any
            logger.info(f"Message ID {outgoing_message_id} sent successfully via Meta API. WAMID: {outgoing_msg.wamid}")
        else:
            # Handle failure from Meta API
            error_info = api_response or {'error': 'Meta API call failed or returned unexpected response.'}
            logger.error(f"Failed to send Message ID {outgoing_message_id} via Meta API. Response: {error_info}")
            outgoing_msg.status = 'failed'
            outgoing_msg.error_details = error_info
            # Retry logic for certain types of failures could be added here
            # For now, we rely on Celery's built-in retry for RequestException type errors.
            # If Meta returns a specific error code that indicates a retryable issue, handle it.
            # Example: if error_info.get('error', {}).get('code') == SOME_RETRYABLE_CODE:
            #    raise self.retry(exc=ValueError("Meta API retryable error"))

    except Exception as e:
        logger.error(f"Exception in send_whatsapp_message_task for Message ID {outgoing_message_id}: {e}", exc_info=True)
        outgoing_msg.status = 'failed'
        outgoing_msg.error_details = {'error': str(e), 'type': type(e).__name__}
        try:
            # Retry the task if it's a network issue or a temporary problem
            # Celery will automatically retry based on max_retries and default_retry_delay.
            # You might want to customize retry conditions.
            raise self.retry(exc=e) # Re-raise to trigger Celery's retry mechanism
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for sending Message ID {outgoing_message_id}.")
            # Send a signal that other apps can listen to, instead of calling them directly.
            message_send_failed.send(sender=self.__class__, message_instance=outgoing_msg)
    finally:
        outgoing_msg.status_timestamp = timezone.now()
        outgoing_msg.save(update_fields=['wamid', 'status', 'error_details', 'status_timestamp'])


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_read_receipt_task(self, wamid: str, config_id: int):
    """
    Celery task to send a read receipt for a given message ID.
    """
    logger.info(f"Task send_read_receipt_task started for WAMID: {wamid}")
    try:
        active_config = MetaAppConfig.objects.get(pk=config_id)
    except MetaAppConfig.DoesNotExist:
        logger.error(f"send_read_receipt_task: MetaAppConfig with ID {config_id} not found. Task cannot proceed.")
        return  # Cannot retry if config is missing

    try:
        api_response = send_read_receipt_api(wamid=wamid, config=active_config)
        # The read receipt API returns {"success": true}. If the response is None or 'success' is not true, it's a failure.
        if not api_response or not api_response.get('success'):
            # The utility function has already logged the specific error. We raise an exception to trigger a retry.
            raise ValueError(f"API call to send read receipt failed for WAMID {wamid}. Response: {api_response}")

    except Exception as e:
        logger.warning(f"Exception in send_read_receipt_task for WAMID {wamid}, will retry. Error: {e}")
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for sending read receipt for WAMID {wamid}.")
