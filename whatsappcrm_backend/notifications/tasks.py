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

    # --- Safety Check ---
    # The main filtering happens in services.py before queuing. This is a final
    # check in case the window closed between queuing and task execution.
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    is_window_open = (
        hasattr(recipient, 'whatsapp_contact') and
        recipient.whatsapp_contact and
        recipient.whatsapp_contact.last_seen >= twenty_four_hours_ago
    )
    
    if not is_window_open:
        error_msg = f"User '{recipient.username}' 24-hour window closed between queuing and dispatch. Last seen: {recipient.whatsapp_contact.last_seen}."
        logger.warning(f"Cannot send notification {notification.id}: {error_msg}")
        notification.status = 'failed'
        notification.error_message = error_msg
        notification.save(update_fields=['status', 'error_message'])
        return

    if notification.channel == 'whatsapp':
        try:
            active_config = MetaAppConfig.objects.get_active_config()
            with transaction.atomic():
                message_obj = Message(
                    contact=recipient.whatsapp_contact, app_config=active_config, direction='out',
                    message_type='text',
                    content_payload={'body': notification.content},
                    status='pending_dispatch',
                    is_system_notification=True # Flag this as a system notification
                )
                created_messages = Message.objects.bulk_create([message_obj])
                message = created_messages[0]

                notification.status = 'sent'
                notification.sent_at = timezone.now()
                notification.save(update_fields=['status', 'sent_at'])
                transaction.on_commit(lambda: send_whatsapp_message_task.delay(message.id, active_config.id))
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
    A scheduled task to find admin users whose 24-hour interaction window is about to close and
    send them a reminder to interact with the bot to keep the window open.
    This task is idempotent and will not re-notify a user within a 23-hour period.
    """
    logger.info("Running scheduled task: check_and_send_24h_window_reminders")
    
    # Define the time window: find users whose last interaction was between 23 and 24 hours ago.
    # This provides a 1-hour "danger zone" to catch them before the window closes.
    window_start = timezone.now() - timedelta(hours=24)
    window_end = timezone.now() - timedelta(hours=23)

    # Find all admin users whose last interaction falls within our target window.
    potential_users_to_remind = User.objects.filter(
        groups__name__in=['Technical Admin', 'Pastoral Team'],
        whatsapp_contact__isnull=False,
        whatsapp_contact__last_seen__gte=window_start,
        whatsapp_contact__last_seen__lt=window_end
    ).distinct()

    if not potential_users_to_remind.exists():
        logger.info("No admin users found with expiring 24-hour windows.")
        return "No users to remind."

    reminder_message_content = (
        "Friendly Reminder 🤖\n\n"
        "Your 24-hour interaction window with the CRM bot is about to close. "
        "To continue receiving real-time alerts, please send any message (e.g., 'status' or 'ok') to this chat now."
    )
    
    # --- Idempotency Check ---
    # Get IDs of users who have already received this specific reminder in the last 23 hours
    # to avoid spamming them if the task runs multiple times.
    recent_reminder_cutoff = timezone.now() - timedelta(hours=23)
    users_already_reminded_ids = Notification.objects.filter(
        recipient__in=potential_users_to_remind,
        created_at__gte=recent_reminder_cutoff,
        content=reminder_message_content
    ).values_list('recipient_id', flat=True)

    # Exclude users who have been reminded recently.
    users_to_remind = potential_users_to_remind.exclude(id__in=users_already_reminded_ids)
    
    if not users_to_remind.exists():
        logger.info("Found users with expiring windows, but they have all been reminded recently. No new reminders sent.")
        return "Users with expiring windows found, but all have been reminded recently."

    from .services import queue_notifications_to_users # Local import to avoid circular dependency issues at module level
    
    # Queue reminders for all eligible users at once.
    user_ids_to_remind = list(users_to_remind.values_list('id', flat=True))
    if user_ids_to_remind:
        queue_notifications_to_users(
            user_ids=user_ids_to_remind,
            message_body=reminder_message_content
        )
        dispatched_count = len(user_ids_to_remind)
        for user_id in user_ids_to_remind:
            logger.info(f"Queued 24h window reminder for User ID: {user_id}.")
        
    return f"Successfully dispatched {dispatched_count} window expiry reminder(s)."