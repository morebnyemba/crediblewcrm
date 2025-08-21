# whatsappcrm_backend/notifications/services.py

import logging
from typing import List, Optional
from django.contrib.auth import get_user_model

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
    related_flow: Optional[Flow] = None
):
    """
    Finds users by ID or group, creates a Notification record for each,
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

    target_users = target_users_query.distinct()

    for user in target_users:
        notification = Notification.objects.create(
            recipient=user,
            channel='whatsapp',
            status='pending',
            content=message_body,
            related_contact=related_contact,
            related_flow=related_flow
        )
        dispatch_notification_task.delay(notification.id)
        logger.info(f"Notifications: Queued Notification ID {notification.id} for user '{user.username}'.")