# stats/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncDate

from conversations.models import Contact, Message
from customer_data.models import Payment
from flows.models import Flow

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
    """When a new message is created, recalculate and broadcast message stats and chart data."""
    if created:
        logger.debug(f"Signal triggered: New message {instance.id}")
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        # --- Stats Card Payload ---
        stats_payload = {
            'messages_sent_24h': Message.objects.filter(direction='out', timestamp__gte=twenty_four_hours_ago).count(),
            'messages_received_24h': Message.objects.filter(direction='in', timestamp__gte=twenty_four_hours_ago).count(),
        }
        broadcast_update('stats_update', stats_payload)

        # --- Conversation Trends Chart Payload ---
        seven_days_ago_start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
        message_trends = Message.objects.filter(timestamp__gte=seven_days_ago_start_of_day)\
            .annotate(date=TruncDate('timestamp'))\
            .values('date')\
            .annotate(incoming_count=Count('id', filter=Q(direction='in')),
                      outgoing_count=Count('id', filter=Q(direction='out')))\
            .order_by('date')
        
        chart_payload = [
            {
                "date": item['date'].strftime('%Y-%m-%d'), 
                "incoming_messages": item['incoming_count'],
                "outgoing_messages": item['outgoing_count'],
                "total_messages": item['incoming_count'] + item['outgoing_count']
            }
            for item in message_trends
        ]
        broadcast_update('chart_update_conversation_trends', chart_payload)

        # --- Bot Performance Chart Payload ---
        bot_perf_payload = {
            "total_incoming_messages_processed": Message.objects.filter(direction='in').count(),
            # Other metrics like automated_resolution_rate would be calculated here if implemented.
        }
        broadcast_update('chart_update_bot_performance', bot_perf_payload)

@receiver(post_save, sender=Contact)
def on_contact_change(sender, instance, created, **kwargs):
    """When a contact is created or updated, broadcast relevant stats."""
    logger.debug(f"Signal triggered: Contact changed {instance.id}, created={created}")
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # --- Stats Card Payload ---
    stats_payload = {
        'new_contacts_today': Contact.objects.filter(first_seen__gte=today_start).count(),
        'total_contacts': Contact.objects.count(),
        'pending_human_handovers': Contact.objects.filter(needs_human_intervention=True).count(),
    }
    broadcast_update('stats_update', stats_payload)

    # --- Activity Log Payload (only for new contacts) ---
    if created:
        activity_payload = {
            "id": f"contact_new_{instance.id}",
            "text": f"New contact: {instance.name or instance.whatsapp_id}",
            "timestamp": instance.first_seen.isoformat(),
            "iconName": "FiUsers", 
            "iconColor": "text-emerald-500"
        }
        broadcast_update('activity_log_add', activity_payload)

@receiver(post_save, sender=Flow)
def on_flow_change(sender, instance, created, **kwargs):
    """When a flow is updated, send an activity log entry."""
    if not created:
        logger.debug(f"Signal triggered: Flow updated {instance.id}")
        activity_payload = {
            "id": f"flow_update_{instance.id}_{instance.updated_at.timestamp()}",
            "text": f"Flow '{instance.name}' was updated.",
            "timestamp": instance.updated_at.isoformat(),
            "iconName": "FiZap", 
            "iconColor": "text-purple-500"
        }
        broadcast_update('activity_log_add', activity_payload)

@receiver(post_save, sender=Payment)
def on_payment_change(sender, instance, created, **kwargs):
    """
    This is a placeholder. A real implementation would check if the status
    changed to 'completed' and then update financial stats.
    """
    # For simplicity, we are not implementing the full financial stat recalculation here,
    # but this is where you would add it.
    pass

@receiver(post_save, sender=Contact)
def on_contact_change_for_intervention(sender, instance, created, **kwargs):
    """
    Specifically checks for human intervention changes to send a real-time notification.
    This relies on the save() call using update_fields=['needs_human_intervention', ...].
    """
    update_fields = kwargs.get('update_fields') or set()
    if instance.needs_human_intervention and ('needs_human_intervention' in update_fields or created):
        logger.info(f"Human intervention needed for contact {instance.id}. Broadcasting notification.")
        notification_payload = {
            "contact_id": instance.id,
            "name": instance.name or instance.whatsapp_id,
            "message": f"Contact '{instance.name or instance.whatsapp_id}' requires human assistance."
        }
        broadcast_update('human_intervention_needed', notification_payload)