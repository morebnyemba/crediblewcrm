# whatsappcrm_backend/meta_integration/tasks.py

import json
import logging
from celery import shared_task, exceptions
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from django.db import close_old_connections

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
        logger.error(f"Message with ID {outgoing_message_id} not found. Task cannot proceed.", extra={'message_id': outgoing_message_id})
        return # Cannot retry if message doesn't exist
    except MetaAppConfig.DoesNotExist:
        logger.error(f"MetaAppConfig with ID {active_config_id} not found. Task cannot proceed.", extra={'config_id': active_config_id, 'message_id': outgoing_message_id})
        # Update message status to failed if config is missing
        try:
            msg_to_fail = Message.objects.get(pk=outgoing_message_id)
            # Check status to avoid sending duplicate notifications if task reruns
            if msg_to_fail.status != 'failed':
                msg_to_fail.status = 'failed'
                msg_to_fail.error_details = {'error': f'MetaAppConfig ID {active_config_id} not found for sending.'}
                msg_to_fail.status_timestamp = timezone.now()
                msg_to_fail.save(update_fields=['status', 'error_details', 'status_timestamp'])
                # Notify admin about this critical configuration error
                message_send_failed.send(sender=self.__class__, message_instance=msg_to_fail)
        except Message.DoesNotExist:
            pass # Already logged above
        return

    try:
        if outgoing_msg.direction != 'out':
            logger.warning(f"Message ID {outgoing_message_id} is not an outgoing message. Skipping.", extra={'message_id': outgoing_message_id})
            return

        # Idempotency check: If already successfully sent, do nothing.
        if outgoing_msg.status == 'sent':
            logger.info(f"Message ID {outgoing_message_id} already marked as sent. Skipping.", extra={'message_id': outgoing_message_id, 'wamid': outgoing_msg.wamid})
            return
        
        # If a task for an already failed message is triggered somehow (e.g., manual re-queue),
        # only proceed if it's an actual Celery retry.
        if outgoing_msg.status == 'failed' and self.request.retries == 0:
             logger.warning(f"Message ID {outgoing_message_id} is already 'failed' and this is not a retry. Skipping.", extra={'message_id': outgoing_message_id})
             return

        # Skip sequential delivery check for system notifications
        if outgoing_msg.is_system_notification:
            logger.info(f"Skipping sequential delivery check for system notification message ID {outgoing_message_id}.", extra={'message_id': outgoing_message_id})
        else:
            # Ensure strict sequential delivery by waiting for preceding messages.
            halting_message = Message.objects.filter(
                contact=outgoing_msg.contact,
                direction='out',
                id__lt=outgoing_message_id,
                status='pending_dispatch'
            ).order_by('-id').first()

            if halting_message:
                logger.warning(
                    f"Halting message ID {outgoing_message_id}. Waiting for preceding message ID {halting_message.id}. Retrying.",
                    extra={
                        'message_id': outgoing_message_id,
                        'contact_id': outgoing_msg.contact.id,
                        'halted_by_message_id': halting_message.id
                    }
                )
                # Retry with a slightly longer countdown for sequential checks.
                raise self.retry(countdown=15)

        logger.info(f"Sending message.", extra={'message_id': outgoing_message_id, 'contact_id': outgoing_msg.contact.id, 'contact_wa_id': outgoing_msg.contact.whatsapp_id})

        if not isinstance(outgoing_msg.content_payload, dict):
            raise ValueError("Message content_payload is not a valid dictionary for sending.")

        api_response = send_whatsapp_message(to_phone_number=outgoing_msg.contact.whatsapp_id,
                                           message_type=outgoing_msg.message_type,
                                           data=outgoing_msg.content_payload,
                                           config=active_config)

        if api_response and api_response.get('messages') and api_response['messages'][0].get('id'):
            outgoing_msg.wamid = api_response['messages'][0]['id']
            outgoing_msg.status = 'sent'
            outgoing_msg.error_details = None
            outgoing_msg.status_timestamp = timezone.now()
            outgoing_msg.save(update_fields=['wamid', 'status', 'error_details', 'status_timestamp'])
            logger.info(f"Message sent successfully via Meta API.", extra={'message_id': outgoing_message_id, 'wamid': outgoing_msg.wamid})
        else:
            error_info = api_response or {'error': 'Meta API call failed or returned unexpected response.'}
            # Log the specific error from Meta if available
            meta_error = error_info.get('error', {})
            logger.error(
                f"Failed to send message via Meta API. Code: {meta_error.get('code')}, Message: {meta_error.get('message')}",
                extra={'message_id': outgoing_message_id, 'contact_id': outgoing_msg.contact.id, 'response': error_info})
            raise ValueError(f"Meta API call failed: {error_info}")

    except Exception as e:
        try:
            # Always attempt to retry on any exception. Celery will raise MaxRetriesExceededError
            # if it can't retry anymore, which is caught below.
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # This is the final failure after all retries are exhausted. This block will NOT be entered
            # if the task fails due to an un-retryable error like a code bug (AttributeError, etc.).
            # Those are caught by the final `except Exception` block in Celery's trace.
            # This block is specifically for when the retry mechanism itself gives up.
            logger.error(f"Max retries exceeded for sending message.", extra={'message_id': outgoing_message_id})
            outgoing_msg.status = 'failed' # type: ignore

            # --- Improved Error Saving ---
            # Try to extract the specific Meta error from the exception if it was a ValueError from the API call
            last_error_details: Any
            error_str = str(e)
            if isinstance(e, ValueError) and "Meta API call failed" in error_str:
                try:
                    # The actual error dict string is in the exception args
                    error_content_str = e.args[0].split('Meta API call failed: ', 1)[1]
                    # Safely evaluate the string to a dict, handling potential single quotes
                    # by replacing them with double quotes for valid JSON.
                    last_error_details = json.loads(error_content_str.replace("'", "\""))
                except (IndexError, AttributeError, json.JSONDecodeError):
                    last_error_details = error_str # Fallback to the full string
            else:
                last_error_details = error_str
            outgoing_msg.error_details = {'error': 'Max retries exceeded.', 'last_error': last_error_details, 'type': type(e).__name__}
            outgoing_msg.status_timestamp = timezone.now() # type: ignore
            outgoing_msg.save(update_fields=['status', 'error_details', 'status_timestamp']) # type: ignore
            message_send_failed.send(sender=self.__class__, message_instance=outgoing_msg)
        except exceptions.Retry as retry_exc:
            # This is the case where Celery is about to retry.
            # We just re-raise the exception to let Celery handle it.
            raise retry_exc


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def send_read_receipt_task(self, wamid: str, config_id: int):
    """
    Celery task to send a read receipt for a given message ID.
    """
    logger.info(f"Sending read receipt.", extra={'wamid': wamid})
    try:
        active_config = MetaAppConfig.objects.get(pk=config_id)
    except MetaAppConfig.DoesNotExist:
        logger.error(f"MetaAppConfig with ID {config_id} not found. Task cannot proceed.", extra={'wamid': wamid, 'config_id': config_id})
        return  # Cannot retry if config is missing

    try:
        api_response = send_read_receipt_api(wamid=wamid, config=active_config)
        # The read receipt API returns {"success": true}. If the response is None or 'success' is not true, it's a failure.
        if not api_response or not api_response.get('success'):
            # The utility function has already logged the specific error. We raise an exception to trigger a retry.
            raise ValueError(f"API call failed. Response: {api_response}")

    except Exception as e:
        logger.warning(f"Exception sending read receipt, will retry.", extra={'wamid': wamid, 'error': str(e)})
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for sending read receipt.", extra={'wamid': wamid})
