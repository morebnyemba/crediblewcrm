# whatsappcrm_backend/notifications/services.py
import logging
from typing import List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from .models import Notification
from .tasks import dispatch_notification_task
from conversations.models import Contact
from flows.models import Flow

logger = logging.getLogger(__name__)
User = get_user_model()

def queue_notifications_to_users(
    message_body: str,
    user_ids: Optional[List[int]] = None,
    group_names: Optional[List[str]] = None,
    related_contact: Optional[Contact] = None,
    related_flow: Optional[Flow] = None,
    channel: str = 'whatsapp'
):
    """
    Finds users by ID or group, filters them to only include those who have
    interacted within the last 24 hours, and creates a Notification record for each.
    """
    if not message_body:
        logger.warning("queue_notifications_to_users called with an empty message_body. Skipping.")
        return

    if not user_ids and not group_names:
        logger.warning("queue_notifications_to_users called without user_ids or group_names. No target users.")
        return

    query = Q()
    if user_ids:
        query |= Q(id__in=user_ids)
    if group_names:
        query |= Q(groups__name__in=group_names)

    all_potential_users = User.objects.filter(query, is_active=True).distinct().select_related('whatsapp_contact')

    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    users_to_notify = []
    
    for user in all_potential_users:
        if hasattr(user, 'whatsapp_contact') and user.whatsapp_contact and user.whatsapp_contact.last_seen >= twenty_four_hours_ago:
            users_to_notify.append(user)
        else:
            last_seen = user.whatsapp_contact.last_seen if hasattr(user, 'whatsapp_contact') and user.whatsapp_contact else 'N/A'
            logger.warning(f"Skipped queuing notification for admin '{user.username}' because their last interaction was at {last_seen}, outside the 24-hour window.")

    if not users_to_notify:
        logger.info("No active admin users found within the 24-hour window. No notifications were queued.")
        return

    notifications_to_create = [
        Notification(recipient=user, channel=channel, status='pending', content=message_body, related_contact=related_contact, related_flow=related_flow)
        for user in users_to_notify
    ]

    created_notifications = Notification.objects.bulk_create(notifications_to_create)
    logger.info(f"Bulk created {len(created_notifications)} notifications for {len(users_to_notify)} eligible admin users.")

    for notification in created_notifications:
        transaction.on_commit(lambda n=notification: dispatch_notification_task.delay(n.id))
        logger.info(f"Notifications: Queued Notification ID {notification.id} for user '{notification.recipient.username}'.")