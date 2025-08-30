# whatsappcrm_backend/notifications/tasks.py

import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from datetime import timedelta

from meta_integration.models import MetaAppConfig
from meta_integration.tasks import send_whatsapp_message_task
from conversations.models import Message, Contact
from .models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()

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
                    message_type='text', content_payload={'body': notification.content}, status='pending_dispatch',
                    is_system_notification=True # Flag this as a system notification
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

@shared_task
def check_and_send_24h_window_reminders():
    """
    A scheduled task to find admin users whose 24-hour interaction window is about to close
    and send them a reminder to interact with the bot to keep the window open.
    """
    logger.info("Running scheduled task: check_and_send_24h_window_reminders")
    
    # Define the time window: between 23h 10m and 23h 20m ago.
    # This gives a 10-minute window for the task to run and catch users.
    window_end = timezone.now() - timedelta(hours=23, minutes=10)
    window_start = timezone.now() - timedelta(hours=23, minutes=20)

    # Find all users who are in the "Technical Admin" or "Pastoral Team" groups
    # and whose last interaction falls within our target window.
    target_users = User.objects.filter(
        groups__name__in=['Technical Admin', 'Pastoral Team'],
        whatsapp_contact__isnull=False,
        whatsapp_contact__last_seen__gte=window_start,
        whatsapp_contact__last_seen__lt=window_end
    ).distinct()

    if not target_users.exists():
        logger.info("No admin users found with expiring 24-hour windows.")
        return "No users to remind."

    reminder_message = (
        "Friendly Reminder 🤖\n\n"
        "Your 24-hour interaction window with the CRM bot is about to close. "
        "To continue receiving real-time alerts, please send any message (e.g., 'status' or 'ok') to this chat now."
    )
    
    dispatched_count = 0
    for user in target_users:
        logger.info(f"Found user '{user.username}' with an expiring window. Last seen: {user.whatsapp_contact.last_seen}. Queuing reminder.")
        # We can call the queueing service directly.
        # This will create a Notification record for auditing.
        from .services import queue_notifications_to_users
        queue_notifications_to_users(
            user_ids=[user.id],
            message_body=reminder_message
        )
        dispatched_count += 1
        
    return f"Dispatched {dispatched_count} window expiry reminders."