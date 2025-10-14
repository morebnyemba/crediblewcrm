# conversations/signals.py
# whatsappcrm_backend/conversations/signals.py

import asyncio
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
import logging

from .models import Message
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)

def run_async(coro):
    """
    Runs a coroutine in a new event loop. This is a safe way to call async
    code from a synchronous context (like a signal handler).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

@receiver(post_save, sender=Message)
def on_new_or_updated_message(sender, instance, created, **kwargs):
    """
    When a Message is saved, serialize it and broadcast it to the
    corresponding conversation group.
    """
    async def send_message_to_group():
        try:
            channel_layer = get_channel_layer()
            if not instance.contact_id:
                return
            group_name = f"conversation_{instance.contact.id}"
            message_data = MessageSerializer(instance).data
            await channel_layer.group_send(group_name, {"type": "chat.message", "message": message_data})
            logger.info(f"Broadcasted message {instance.id} to group {group_name}")
        except Exception as e:
            logger.error(f"Error in on_new_or_updated_message signal for message {instance.id}: {e}", exc_info=True)
            
    run_async(send_message_to_group())