# whatsappcrm_backend/customer_data/signals.py

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Payment
from meta_integration.tasks import send_whatsapp_message_task
from conversations.models import Message
from django.utils import timezone

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Payment)
def handle_event_booking_payment_completion(sender, instance, created, **kwargs):
    """
    Listens for a Payment being saved. If it's a completed event registration
    payment, it updates the corresponding EventBooking status to 'confirmed'
    and notifies the user.
    """
    # We only care about updates where the status is now 'completed'
    if not created and instance.status == 'completed' and instance.payment_type == 'event_registration':
        # Check if the payment is linked to an event booking
        if hasattr(instance, 'event_booking') and instance.event_booking:
            booking = instance.event_booking
            # Only update if the booking is still pending verification
            if booking.status == 'pending_payment_verification':
                booking.status = 'confirmed'
                booking.save(update_fields=['status'])
                logger.info(f"EventBooking {booking.id} status updated to 'confirmed' for completed Payment {instance.id}.")

                # Send a confirmation notification to the user
                if booking.contact and booking.event:
                    message_text = (
                        f"Great news! 🎉 Your payment for the event *{booking.event.title}* has been confirmed.\n\n"
                        "Your booking is now complete. We look forward to seeing you there!"
                    )
                    
                    # Create and dispatch the message via Celery task
                    @transaction.on_commit
                    def dispatch_notification():
                        if booking.contact.app_config:
                            message = Message.objects.create(
                                contact=booking.contact,
                                app_config=booking.contact.app_config,
                                direction='out',
                                message_type='text',
                                content_payload={'body': message_text},
                                status='pending_dispatch',
                                timestamp=timezone.now()
                            )
                            send_whatsapp_message_task.delay(message.id, booking.contact.app_config.id)
                            logger.info(f"Queued booking confirmation notification for EventBooking {booking.id} to Contact {booking.contact.id}.")
                    dispatch_notification()