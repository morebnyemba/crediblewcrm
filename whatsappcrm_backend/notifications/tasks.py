# whatsappcrm_backend/notifications/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from meta_integration.models import MetaAppConfig
from meta_integration.tasks import send_whatsapp_message_task
from conversations.models import Message, Contact
from .models import Notification

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def dispatch_notification_task(self, notification_id: int):
    """
    Fetches a Notification object and attempts to send it via its specified channel.
    Updates the notification status based on the outcome.
    """
    try:
        notification = Notification.objects.select_related('recipient', 'recipient__whatsapp_contact').get(pk=notification_id)
    except Notification.DoesNotExist:
        logger.error(f"Notification with ID {notification_id} not found. Aborting task.")
        return

    if notification.status != 'pending':
        logger.warning(f"Notification {notification_id} is not in 'pending' state (state is '{notification.status}'). Skipping.")
        return

    recipient = notification.recipient
    if not hasattr(recipient, 'whatsapp_contact') or not recipient.whatsapp_contact:
        error_msg = f"User '{recipient.username}' has no linked WhatsApp contact."
        logger.warning(f"Cannot send notification {notification.id}: {error_msg}")
        notification.status = 'failed'
        notification.error_message = error_msg
        notification.save(update_fields=['status', 'error_message'])
        return

    if notification.channel == 'whatsapp':
        try:
            with transaction.atomic():
                active_config = MetaAppConfig.objects.get_active_config()
                message = Message.objects.create(
                    contact=recipient.whatsapp_contact, app_config=active_config, direction='out',
                    message_type='text', content_payload={'body': notification.content}, status='pending_dispatch'
                )
                notification.status = 'sent'
                notification.sent_at = timezone.now()
                notification.save(update_fields=['status', 'sent_at'])
                send_whatsapp_message_task.delay(message.id, active_config.id)
                logger.info(f"Successfully dispatched notification {notification.id} as Message {message.id}.")
        except Exception as e:
            logger.error(f"Failed to dispatch notification {notification.id} for user '{recipient.username}'. Error: {e}", exc_info=True)
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save(update_fields=['status', 'error_message'])
            self.retry(exc=e)