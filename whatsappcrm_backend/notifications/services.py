# whatsappcrm_backend/notifications/services.py
import logging
from typing import List, Optional
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q

from .tasks import dispatch_notification_task
from .models import Notification
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
    Finds a unique set of users by ID or group, filters them to only include those who have
    interacted within the last 24 hours, and queues a notification for each.
    """
    if not message_body:
        logger.warning("queue_notifications_to_users called with an empty message_body. Skipping.")
        return

    if not user_ids and not group_names:
        logger.warning("queue_notifications_to_users called without user_ids or group_names. No target users.")
        return

    # Build a query that finds all potential users by ID or group membership
    query = Q()
    if user_ids:
        query |= Q(id__in=user_ids)
    if group_names:
        query |= Q(groups__name__in=group_names)

    # Use .distinct() to ensure each user is only selected once
    all_potential_users = User.objects.filter(query, is_active=True).distinct().select_related('whatsapp_contact')

    # Partition users into those who can be notified and those who can't
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    users_to_notify = []
    skipped_users_for_log = []

    for user in all_potential_users:
        # Check if user has a linked contact and if that contact was seen recently
        if hasattr(user, 'whatsapp_contact') and user.whatsapp_contact and user.whatsapp_contact.last_seen >= twenty_four_hours_ago:
            users_to_notify.append(user)
        else:
            skipped_users_for_log.append(user)

    # Log skipped users
    for user in skipped_users_for_log:
        last_seen = user.whatsapp_contact.last_seen if hasattr(user, 'whatsapp_contact') and user.whatsapp_contact else 'N/A'
        logger.warning(
            f"Skipped notification for user '{user.username}' because their last interaction "
            f"was at {last_seen}, which is outside the 24-hour window."
        )

    if not users_to_notify:
        logger.info("No active users found within the 24-hour window. No notifications were queued.")
        return

    # Bulk create notifications for efficiency
    notifications_to_create = [
        Notification(
            recipient=user,
            channel=channel,
            status='pending',
            content=message_body,
            related_contact=related_contact,
            related_flow=related_flow
        )
        for user in users_to_notify
    ]

    # The `bulk_create` method returns the list of created objects
    created_notifications = Notification.objects.bulk_create(notifications_to_create)
    logger.info(f"Bulk created {len(created_notifications)} notifications for {len(users_to_notify)} unique users.")

    # Dispatch tasks after the transaction commits
    for notification in created_notifications:
        transaction.on_commit(lambda: dispatch_notification_task.delay(notification.id))
        logger.info(f"Notifications: Queued Notification ID {notification.id} for user '{notification.recipient.username}' (to be dispatched on transaction commit).")