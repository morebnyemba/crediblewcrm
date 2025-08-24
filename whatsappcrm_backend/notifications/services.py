# whatsappcrm_backend/notifications/services.py

import logging
from typing import List, Optional
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .tasks import dispatch_notification_task
from .models import Notification
from conversations.models import Contact
from flows.models import Flow

logger = logging.getLogger(__name__)

User = get_user_model()

def queue_notifications_to_users(
    user_ids: Optional[List[int]] = None,
    group_names: Optional[List[str]] = None,
    message_body: str = "",
    related_contact: Optional[Contact] = None,
    related_flow: Optional[Flow] = None,
):
    """
    Finds users by ID or group, filters them to only include those who have
    interacted within the last 24 hours, creates a Notification record for each,
    and queues a task to send it.
    """
    if not message_body:
        logger.warning("queue_notifications_to_users called with an empty message_body. Skipping.")
        return

    target_users_query = User.objects.none()
    if user_ids:
        target_users_query |= User.objects.filter(id__in=user_ids)
    if group_names:
        target_users_query |= User.objects.filter(groups__name__in=group_names)

    # Filter for users with an associated WhatsApp contact that has been seen recently.
    # This ensures we only send free-form messages within Meta's 24-hour window.
    twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
    
    # We need to filter based on the 'last_seen' of the user's associated WhatsApp contact.
    target_users = target_users_query.distinct().select_related('whatsapp_contact').filter(
        whatsapp_contact__isnull=False,
        whatsapp_contact__last_seen__gte=twenty_four_hours_ago
    )

    for user in target_users:
        notification = Notification.objects.create(
            recipient=user,
            channel='whatsapp',
            status='pending',
            content=message_body,
            related_contact=related_contact,
            related_flow=related_flow
        )
        # Use transaction.on_commit to prevent a race condition where the task
        # executes before the notification object is committed to the database.
        transaction.on_commit(lambda: dispatch_notification_task.delay(notification.id))
        logger.info(f"Notifications: Queued Notification ID {notification.id} for user '{user.username}' (to be dispatched on transaction commit).")

    # Log users who were filtered out
    all_potential_users = target_users_query.distinct().select_related('whatsapp_contact')
    skipped_users = all_potential_users.exclude(id__in=target_users.values_list('id', flat=True))
    for user in skipped_users:
        last_seen = user.whatsapp_contact.last_seen if hasattr(user, 'whatsapp_contact') and user.whatsapp_contact else 'N/A'
        logger.warning(
            f"Skipped notification for user '{user.username}' because their last interaction "
            f"was at {last_seen}, which is outside the 24-hour window."
        )