# whatsappcrm_backend/customer_data/tasks.py

import logging
from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from uuid import UUID

from .models import Payment
from meta_integration.models import MetaAppConfig
from meta_integration.utils import download_whatsapp_media

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5) # Retry after 5 mins
def process_proof_of_payment_image(self, payment_id: str, wamid: str):
    """
    Celery task to download a proof of payment image from WhatsApp
    and save its URL to a Payment record.
    """
    try:
        payment = Payment.objects.get(id=UUID(payment_id))
    except (Payment.DoesNotExist, ValueError):
        logger.error(f"process_proof_of_payment_image: Payment with ID {payment_id} not found. Task will not be retried.")
        return f"Payment not found: {payment_id}"

    if payment.proof_of_payment_url:
        logger.info(f"Payment {payment_id} already has a proof of payment URL. Skipping download.")
        return f"Proof of payment already exists for Payment {payment_id}."

    try:
        config = MetaAppConfig.objects.get_active_config()
    except (MetaAppConfig.DoesNotExist, MetaAppConfig.MultipleObjectsReturned) as e:
        logger.error(f"Cannot get unique active MetaAppConfig for payment {payment_id}. Retrying. Error: {e}")
        self.retry(exc=e)

    logger.info(f"Starting download of proof of payment for Payment {payment_id} (WAMID: {wamid}).")
    download_result = download_whatsapp_media(wamid, config)

    if not download_result:
        logger.error(f"Failed to download media for WAMID {wamid} for payment {payment_id}. Retrying.")
        self.retry()

    image_bytes, mime_type = download_result
    
    file_extension = mime_type.split('/')[-1] if mime_type and '/' in mime_type else 'jpg'
    safe_extension = ''.join(c for c in file_extension if c.isalnum())
    filename = f"payment_proofs/{payment.created_at.year}/{payment.created_at.month}/{payment_id}.{safe_extension}"

    try:
        # Save the file and store its relative path, not the full URL.
        saved_path = default_storage.save(filename, ContentFile(image_bytes))
        payment.proof_of_payment_url = saved_path
        payment.save(update_fields=['proof_of_payment_url', 'updated_at'])
        logger.info(f"Successfully saved proof of payment for Payment {payment_id} at path: {saved_path}")
    except Exception as e:
        logger.error(f"Failed to save proof of payment file for payment {payment_id}. Error: {e}", exc_info=True)
        self.retry(exc=e)