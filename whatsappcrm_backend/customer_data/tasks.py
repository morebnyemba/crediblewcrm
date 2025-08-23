# whatsappcrm_backend/customer_data/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from uuid import UUID

from .models import Payment, MemberProfile
from meta_integration.models import MetaAppConfig
from meta_integration.utils import download_whatsapp_media

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5) # Retry after 5 mins
def process_proof_of_payment_image(self, payment_id: str, wamid: str):
    """
    Celery task to download a proof of payment image from WhatsApp
    and save it to the Payment record's ImageField.
    """
    try:
        payment = Payment.objects.get(id=UUID(payment_id))
    except (Payment.DoesNotExist, ValueError):
        logger.error(f"process_proof_of_payment_image: Payment with ID {payment_id} not found. Task will not be retried.")
        return f"Payment not found: {payment_id}"

    if payment.proof_of_payment:
        logger.info(f"Payment {payment_id} already has a proof of payment. Skipping download.")
        return f"Proof of payment already exists for Payment {payment_id}."

    # Get active Meta App Config
    try:
        config = MetaAppConfig.objects.get_active_config()
    except (MetaAppConfig.DoesNotExist, MetaAppConfig.MultipleObjectsReturned) as e:
        logger.error(f"Cannot get unique active MetaAppConfig for payment {payment_id}. Retrying. Error: {e}")
        raise self.retry(exc=e)

    logger.info(f"Starting download of proof of payment for Payment {payment_id} (WAMID: {wamid}).")

    # Attempt to download the WhatsApp media
    download_result = download_whatsapp_media(wamid, config)

    # Check download
    if not download_result:
        logger.error(f"Failed to download media for WAMID {wamid} for payment {payment_id}. This was attempt {self.request.retries + 1}/{self.max_retries + 1}.")
        try:
            raise self.retry(exc=ValueError(f"Media download failed for WAMID {wamid}"))
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for downloading media for payment {payment_id}.")
            payment.notes = (payment.notes or "") + f"\n[SYSTEM] Failed to download proof of payment from WhatsApp after multiple retries (WAMID: {wamid})."
            payment.save(update_fields=['notes'])
            return # End task gracefully

    # Extract information
    image_bytes, mime_type = download_result
    
    # Create a unique filename
    # The ImageField's 'upload_to' attribute will handle the directory structure.
    file_extension = mime_type.split('/')[-1] if mime_type and '/' in mime_type else 'jpg'
    safe_extension = ''.join(c for c in file_extension if c.isalnum()) # Sanitize file extension
    filename = f"{payment_id}.{safe_extension}"

    try:
        # Use the .save() method of the ImageField.
        # This handles saving the file to storage and updating the model field's path.
        payment.proof_of_payment.save(filename, ContentFile(image_bytes), save=True)
        logger.info(f"Successfully saved proof of payment for Payment {payment_id} at path: {payment.proof_of_payment.name}")
    except Exception as e:
        logger.error(f"Failed to save proof of payment file for payment {payment_id}. Retrying. Error: {e}", exc_info=True)
        self.retry(exc=e)

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 2) # Retry after 2 mins
def send_birthday_whatsapp_message(self, member_profile_id: int):
    """
    Sends a personalized birthday wish to a specific member.
    """
    # Local import to break circular dependency
    from meta_integration.tasks import send_whatsapp_message_task
    from conversations.models import Message

    try:
        member = MemberProfile.objects.select_related('contact').get(contact_id=member_profile_id)
        contact = member.contact
        if not contact:
            logger.warning(f"MemberProfile {member_profile_id} has no associated contact. Cannot send birthday message.")
            return

        active_config = MetaAppConfig.objects.get_active_config()

        first_name = member.first_name or contact.name or "Friend"
        
        message_text = (
            f"Happy Birthday, {first_name}! 🎂🎉\n\n"
            "May your day be filled with joy, laughter, and countless blessings. We are so grateful to have you as part of our church family.\n\n"
            "\"The Lord bless you and keep you; the Lord make his face shine on you and be gracious to you; the Lord turn his face toward you and give you peace.\" - Numbers 6:24-26\n\n"
            "With love,\n"
            "Your Church Family"
        )

        outgoing_msg = Message.objects.create(
            contact=contact, app_config=active_config, direction='out',
            message_type='text', content_payload={'body': message_text},
            status='pending_dispatch', timestamp=timezone.now()
        )
        send_whatsapp_message_task.delay(outgoing_msg.id, active_config.id)
        logger.info(f"Queued birthday message for MemberProfile {member.contact_id} ({contact.whatsapp_id}).")

    except MemberProfile.DoesNotExist:
        logger.error(f"send_birthday_whatsapp_message: MemberProfile with ID {member_profile_id} not found. Task will not be retried.")
    except (MetaAppConfig.DoesNotExist, MetaAppConfig.MultipleObjectsReturned) as e:
        logger.error(f"Cannot get unique active MetaAppConfig for sending birthday message to contact {contact.id}. Retrying. Error: {e}")
        self.retry(exc=e)
    except Exception as e:
        logger.error(f"An unexpected error occurred in send_birthday_whatsapp_message for member {member_profile_id}: {e}", exc_info=True)
        self.retry(exc=e)

@shared_task
def check_for_birthdays_and_dispatch_messages():
    """
    Daily task to find members whose birthday is today and dispatch individual message tasks.
    This task is intended to be run by Celery Beat.
    """
    today = timezone.now().date()
    logger.info(f"Running daily birthday check for {today.strftime('%Y-%m-%d')}.")
    
    birthday_members = MemberProfile.objects.filter(
        date_of_birth__month=today.month,
        date_of_birth__day=today.day
    ).exclude(date_of_birth__isnull=True)

    if not birthday_members.exists():
        logger.info("No members with a birthday today.")
        return "No birthdays found today."

    logger.info(f"Found {birthday_members.count()} member(s) with a birthday today. Dispatching messages...")
    for member in birthday_members:
        send_birthday_whatsapp_message.delay(member.pk)
    
    return f"Dispatched {birthday_members.count()} birthday message tasks."