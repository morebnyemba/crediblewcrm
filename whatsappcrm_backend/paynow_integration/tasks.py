# paynow_integration/tasks.py
import logging
from typing import Optional
from celery import shared_task
import random
from django.db import transaction
from django.utils import timezone

from .services import PaynowService
from meta_integration.utils import send_whatsapp_message, create_text_message_data
from customer_data.models import Payment

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _fail_payment_in_db(payment_obj: Payment, reason: str) -> Optional[Payment]:
    """
    Internal helper to mark a Payment as FAILED in the database.
    This is NOT a Celery task. It returns the failed payment on success, or None.
    """
    log_prefix = f"[DB Fail Helper - Ref: {payment_obj.id}]"
    logger.warning(f"{log_prefix} Attempting to fail payment in DB. Reason: {reason}")

    payment_to_fail = None
    try:
        with transaction.atomic():
            # Atomically fetch and lock the payment ONLY if it's still PENDING.
            payment_to_fail = Payment.objects.select_for_update().get(
                pk=payment_obj.pk,
                status='pending'
            )
            
            payment_to_fail.status = 'failed'
            payment_to_fail.notes = (payment_to_fail.notes or "") + f"\nFailure reason: {reason[:255]}"
            payment_to_fail.save(update_fields=['status', 'notes', 'updated_at'])
            logger.info(f"{log_prefix} Successfully marked payment as FAILED in the database.")
            
    except Payment.DoesNotExist:
        # This is not an error. It means the payment was already processed.
        logger.info(
            f"{log_prefix} Payment was not in PENDING state "
            "when attempting to fail. It was likely already processed. No action taken."
        )
        return None

    return payment_to_fail

def _fail_payment_and_notify_user(payment_obj: Payment, reason: str):
    """
    Marks a payment as failed in the DB and sends a notification to the user.
    """
    log_prefix = f"[Fail & Notify - Ref: {payment_obj.id}]"
    failed_payment = _fail_payment_in_db(payment_obj, reason)
    
    if failed_payment and failed_payment.contact:
        # If the payment was successfully marked as failed, notify the user.
        send_payment_failure_notification_task.delay(str(failed_payment.id))
    elif not failed_payment:
        logger.info(f"{log_prefix} Payment was not failed in DB (likely already processed), so no notification will be sent.")
    elif not payment_obj.contact:
        logger.warning(f"{log_prefix} Payment was failed in DB, but no contact is associated to send notification.")

# --- Celery Tasks ---

@shared_task(name="paynow_integration.send_payment_failure_notification_task")
def send_payment_failure_notification_task(payment_id: str):
    """
    Sends a WhatsApp message to the user notifying them of a failed payment.
    """
    log_prefix = f"[Failure Notif Task - Ref: {payment_id}]"
    logger.info(f"{log_prefix} Preparing to send failure notification.")
    try:
        payment = Payment.objects.get(id=payment_id)
        contact_to_notify = payment.contact
        
        if not contact_to_notify:
            logger.error(f"{log_prefix} Could not find contact associated with payment to send failure notification.")
            return

        failure_message = f"❌ We're sorry, but your contribution of {payment.currency} {payment.amount:.2f} could not be processed. Please try again later. (Ref: {str(payment.id)[:8]})"
        message_data = create_text_message_data(text_body=failure_message)
        send_whatsapp_message(to_phone_number=contact_to_notify.whatsapp_id, message_type='text', data=message_data)
        logger.info(f"{log_prefix} Successfully sent failure notification to user {contact_to_notify.whatsapp_id}.")
    except Payment.DoesNotExist:
        logger.error(f"{log_prefix} Could not find payment to send failure notification.")
    except Exception as e:
        logger.error(f"{log_prefix} Error sending failure notification: {e}", exc_info=True)

@shared_task(name="paynow_integration.send_giving_confirmation_whatsapp")
def send_giving_confirmation_whatsapp(payment_id: str):
    """
    Sends a WhatsApp message to the user confirming their successful contribution.
    """
    log_prefix = f"[Giving Confirm Task - Ref: {payment_id}]"
    logger.info(f"{log_prefix} Preparing to send giving confirmation.")
    try:
        payment = Payment.objects.get(id=payment_id, status='completed')
        contact_to_notify = payment.contact

        if not contact_to_notify:
            logger.error(f"{log_prefix} Could not find contact associated with payment to send confirmation.")
            return

        confirmation_message = f"✅ Thank you for your generous contribution of {payment.currency} {payment.amount:.2f}! Your support is greatly appreciated. May God bless you. (Ref: {str(payment.id)[:8]})"
        message_data = create_text_message_data(text_body=confirmation_message)
        send_whatsapp_message(to_phone_number=contact_to_notify.whatsapp_id, message_type='text', data=message_data)
        logger.info(f"{log_prefix} Successfully sent giving confirmation to user {contact_to_notify.whatsapp_id}.")
    except Payment.DoesNotExist:
        logger.error(f"{log_prefix} Could not find completed payment to send confirmation.")
    except Exception as e:
        logger.error(f"{log_prefix} Error sending giving confirmation: {e}", exc_info=True)

@shared_task(name="paynow_integration.poll_paynow_transaction_status", bind=True, max_retries=10, default_retry_delay=120)
def poll_paynow_transaction_status(self, payment_id: str):
    """
    Polls Paynow to get the transaction status and updates the Payment record accordingly.
    """
    log_prefix = f"[Poll Task - Ref: {payment_id}]"
    logger.info(f"{log_prefix} Polling Paynow status. Attempt {self.request.retries + 1}/{self.max_retries + 1}.")
    try:
        with transaction.atomic():
            # Lock the Payment row to prevent race conditions from IPNs or other tasks.
            pending_payment = Payment.objects.select_for_update().get(id=payment_id, status='pending')
            
            paynow_service = PaynowService()
            poll_url = pending_payment.external_data.get('poll_url')
            if not poll_url:
                logger.error(f"{log_prefix} Poll URL not found. Failing payment.")
                _fail_payment_and_notify_user(pending_payment, "Could not poll status: Poll URL missing.")
                return # Stop execution

            logger.debug(f"{log_prefix} Checking poll URL: {poll_url}")
            status_response = paynow_service.check_transaction_status(poll_url)
            
            if status_response['success']:
                paynow_status = status_response.get('status', 'unknown').lower()
                logger.info(f"{log_prefix} Paynow status received: '{paynow_status}'.")

                if paynow_status == 'paid':
                    pending_payment.status = 'completed'
                    pending_payment.notes = (pending_payment.notes or "") + f"\nPaynow Ref: {pending_payment.transaction_reference}"
                    pending_payment.save(update_fields=['status', 'notes', 'updated_at'])
                    
                    logger.info(f"{log_prefix} Successfully processed payment {pending_payment.id}. Amount: {pending_payment.amount}.")
                    
                    # Send confirmation to user
                    send_giving_confirmation_whatsapp.delay(payment_id=str(pending_payment.id))
                    return # Task is complete

                elif paynow_status in ['cancelled', 'failed', 'disputed']:
                    reason = f"Paynow transaction status was '{paynow_status}'."
                    logger.warning(f"{log_prefix} Failing payment due to status: '{paynow_status}'.")
                    _fail_payment_and_notify_user(pending_payment, reason)
                    return # Task is complete

                else: # 'pending', 'created', 'sent', etc.
                    # Implement exponential backoff with jitter to reduce load on Paynow's servers.
                    retry_delay = 60 * (2 ** self.request.retries)
                    retry_delay_with_jitter = retry_delay + random.randint(0, 15)
                    logger.info(f"{log_prefix} Transaction is still pending with status '{paynow_status}'. Retrying in {retry_delay_with_jitter} seconds.")
                    self.retry(exc=Exception(f"Transaction is still pending. Current status: {paynow_status}"), countdown=retry_delay_with_jitter)
            else:
                error_msg = status_response.get('message', 'Unknown API error')
                logger.error(f"{log_prefix} Failed to get Paynow status: {error_msg}. Retrying task.")
                self.retry(exc=Exception(f"Failed to get Paynow status: {error_msg}"))

    except Payment.DoesNotExist:
        logger.info(f"{log_prefix} Payment not found or not PENDING. It was likely processed by another task. Stopping poll.")
    except Exception as e:
        logger.error(f"{log_prefix} Unhandled error during polling: {e}", exc_info=True)
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"{log_prefix} Max retries exceeded. Attempting to fail payment.")
            try:
                payment_to_fail = Payment.objects.get(id=payment_id, status='pending')
                _fail_payment_and_notify_user(payment_to_fail, f"Polling failed after max retries: {str(e)[:100]}")
            except Payment.DoesNotExist:
                logger.warning(f"{log_prefix} Could not find payment to fail after max retries (it might have been processed or failed already).")
            except Exception as final_fail_exc:
                logger.critical(f"{log_prefix} Could not fail payment after max retries: {final_fail_exc}")

@shared_task(name="paynow_integration.process_paynow_ipn_task")
def process_paynow_ipn_task(ipn_data: dict):
    """
    Processes a Paynow IPN message. It verifies the IPN hash, then triggers
    the polling task to confirm the transaction status before updating the database.
    """
    reference = ipn_data.get('reference')
    if not reference:
        logger.error("[IPN Task] Received IPN data without a reference. Cannot process.")
        return

    log_prefix = f"[IPN Task - Ref: {reference}]"
    logger.info(f"{log_prefix} Starting to process IPN data: {ipn_data}")

    paynow_service = PaynowService()
    if not paynow_service.verify_ipn_hash(ipn_data):
        logger.error(f"{log_prefix} IPN hash verification failed. Discarding message.")
        return

    logger.info(f"{log_prefix} IPN hash verified successfully. Triggering status poll.")

    try:
        # Check if the payment is still in a state that needs processing.
        # The reference from Paynow is our Payment model's UUID (pk).
        if Payment.objects.filter(pk=reference, status='pending').exists():
            poll_paynow_transaction_status.delay(payment_id=reference)
            logger.info(f"{log_prefix} Polling task has been scheduled to finalize the payment.")
        else:
            logger.info(f"{log_prefix} Payment is not in PENDING state. It was likely already processed. No action taken.")

    except Exception as e:
        logger.error(f"{log_prefix} An unexpected error occurred while triggering the poll task: {e}", exc_info=True)
