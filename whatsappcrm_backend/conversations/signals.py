# conversations/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Message
from .serializers import MessageSerializer

import logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=Message)
def on_new_or_updated_message(sender, instance, created, **kwargs):
    """
    When a Message is saved, serialize it and broadcast it to the
    corresponding conversation group.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("Channel layer not available. Cannot broadcast message.")
            return

        contact_id = instance.contact_id
        if not contact_id:
            return

        conversation_group_name = f'conversation_{contact_id}'
        serializer = MessageSerializer(instance)

        async_to_sync(channel_layer.group_send)(
            conversation_group_name,
            {'type': 'chat.message', 'message': serializer.data}
        )
        logger.info(f"Broadcasted message {instance.id} to group {conversation_group_name}")
    except Exception as e:
        logger.error(f"Error in on_new_or_updated_message signal for message {instance.id}: {e}", exc_info=True)