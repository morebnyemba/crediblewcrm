# stats/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from datetime import timedelta

from conversations.models import Contact, Message
from customer_data.models import Payment

import logging
logger = logging.getLogger(__name__)

def broadcast_update(update_type, payload):
    """Helper function to send updates to the dashboard group."""
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            'dashboard_updates',
            {
                'type': 'dashboard.update', # This corresponds to the method name in the consumer
                'update_type': update_type,
                'payload': payload
            }
        )

@receiver(post_save, sender=Message)
def on_new_message(sender, instance, created, **kwargs):
    """When a new message is created, recalculate and broadcast message stats."""
    if created:
        logger.debug(f"Signal triggered: New message {instance.id}")
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        payload = {
            'messages_sent_24h': Message.objects.filter(direction='out', timestamp__gte=twenty_four_hours_ago).count(),
            'messages_received_24h': Message.objects.filter(direction='in', timestamp__gte=twenty_four_hours_ago).count(),
        }
        broadcast_update('stats_update', payload)

@receiver(post_save, sender=Contact)
def on_contact_change(sender, instance, created, **kwargs):
    """When a contact is created or updated, broadcast relevant stats."""
    logger.debug(f"Signal triggered: Contact changed {instance.id}, created={created}")
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    payload = {
        'new_contacts_today': Contact.objects.filter(first_seen__gte=today_start).count(),
        'total_contacts': Contact.objects.count(),
        'pending_human_handovers': Contact.objects.filter(needs_human_intervention=True).count(),
    }
    broadcast_update('stats_update', payload)

@receiver(post_save, sender=Payment)
def on_payment_change(sender, instance, created, **kwargs):
    """
    This is a placeholder. A real implementation would check if the status
    changed to 'completed' and then update financial stats.
    """
    # For simplicity, we are not implementing the full financial stat recalculation here,
    # but this is where you would add it.
    pass