# whatsappcrm_backend/customer_data/utils.py

import logging
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.db import IntegrityError

from conversations.models import Contact
from .models import MemberProfile, Payment, PaymentHistory, PrayerRequest
from .tasks import process_proof_of_payment_image
from church_services.models import Event, EventBooking

logger = logging.getLogger(__name__)

def record_payment(
    contact: Contact,
    amount_str: str,
    payment_type: str,
    currency: str = 'USD',
    payment_method: str = 'whatsapp_flow',
    transaction_ref: str = None,
    notes: str = None,
    proof_of_payment_wamid: str = None,
    status: str = None
) -> tuple[Payment | None, dict | None]:
    """
    Creates a Payment record for a contact and an associated history entry.

    Args:
        contact: The Contact object making the payment.
        amount_str: The amount of the payment as a string.
        payment_type: The type of payment (e.g., 'tithe', 'offering').
        currency: The currency code (e.g., 'USD').
        payment_method: The method of payment.
        transaction_ref: An optional external transaction reference.
        notes: Optional internal notes for the payment.
        proof_of_payment_wamid: Optional WAMID of an uploaded proof of payment image.
        status: Optional status to set for the payment. If not provided, it's inferred.

    Returns:
        A tuple of (Payment object, confirmation_action_dict), or (None, None) if an error occurred.
    """
    logger.info(
        f"Attempting to record payment for contact {contact.id} ({contact.whatsapp_id}). "
        f"Amount: '{amount_str}', Type: '{payment_type}', Method: '{payment_method}', "
        f"Status: '{status}', WAMID: '{proof_of_payment_wamid}'"
    )
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            logger.warning(f"Attempted to record a non-positive payment amount ({amount}) for contact {contact.id} ({contact.whatsapp_id}). Aborting.")
            return None, None
    except (InvalidOperation, TypeError):
        logger.error(f"Invalid amount '{amount_str}' provided for payment for contact {contact.id} ({contact.whatsapp_id}). Cannot convert to Decimal.")
        return None, None

    valid_payment_types = [choice[0] for choice in Payment.PAYMENT_TYPE_CHOICES]
    if payment_type not in valid_payment_types:
        logger.warning(f"Invalid payment_type '{payment_type}' for contact {contact.id} ({contact.whatsapp_id}). Defaulting to 'other'.")
        payment_type = 'other'

    try:
        with transaction.atomic():
            member_profile = MemberProfile.objects.filter(contact=contact).first()

            # Determine status and confirmation message based on payment method
            payment_status = status
            is_manual_payment = payment_method == 'manual_payment'
            if not payment_status:
                payment_status = 'pending' if is_manual_payment else 'completed'

            # --- FIX: Always prioritize 'pending_verification' if proof is provided ---
            # This ensures that even if a default status like 'pending' is passed,
            # it gets correctly upgraded if there's a proof of payment to verify.
            if proof_of_payment_wamid:
                payment_status = 'pending_verification'
                
            logger.debug(
                f"Creating Payment object for contact {contact.id} with: "
                f"Amount={amount}, Currency={currency}, Type={payment_type}, "
                f"Method={payment_method}, Status={payment_status}"
            )
            payment = Payment.objects.create(
                contact=contact, member=member_profile, amount=amount, currency=currency,
                payment_type=payment_type, payment_method=payment_method,
                status=payment_status, transaction_reference=transaction_ref, notes=notes
            )
            history_note = f"Payment recorded via flow for contact {contact.whatsapp_id}."
            if payment_status == 'pending_verification':
                history_note = f"Manual payment with proof submitted via flow for contact {contact.whatsapp_id}. Awaiting verification."
            elif is_manual_payment:
                history_note = f"Manual payment initiated via flow for contact {contact.whatsapp_id}. Awaiting confirmation."

            PaymentHistory.objects.create(payment=payment, status=payment_status, notes=history_note)
            
            # If proof of payment is provided, trigger the background download task
            if proof_of_payment_wamid and payment:
                # Use transaction.on_commit to ensure the task runs only after the payment record is committed to the DB.
                # This prevents a race condition where the Celery worker picks up the task before the transaction is complete.
                transaction.on_commit(
                    lambda: process_proof_of_payment_image.delay(payment_id=str(payment.id), wamid=proof_of_payment_wamid)
                )
                logger.info(f"Scheduled background task to download proof of payment for payment {payment.id}.")

            # Create confirmation message action
            if payment_status == 'pending_verification':
                # This message is now sent from the flow definition itself for better control.
                # We will not generate a confirmation action here for this status.
                confirmation_action = None
            elif is_manual_payment:
                ref_text = f" using reference: *{transaction_ref}*" if transaction_ref else ""
                # This is for a manual payment pledge without immediate proof.
                confirmation_message_text = (
                    f"Thank you for your pledge! 🙏\n\n"
                    f"We have recorded your pending contribution of *{amount} {currency}* for *{payment.get_payment_type_display()}*{ref_text}.\n\n"
                    f"Our bookkeeper will confirm your payment shortly. You will receive a final confirmation once it's processed."
                )
            else:
                confirmation_message_text = (
                    f"Thank you for your contribution! 🙏\n\n"
                    f"We have successfully recorded your payment of *{amount} {currency}* for *{payment.get_payment_type_display()}*.\n\n"
                    f"Your transaction ID is: {payment.id}"
                )
            
            if 'confirmation_message_text' in locals():
                confirmation_action = {
                    'type': 'send_whatsapp_message',
                    'recipient_wa_id': contact.whatsapp_id,
                    'message_type': 'text',
                    'data': {'body': confirmation_message_text}
                }

            logger.info(f"Successfully recorded payment {payment.id} of {amount} {currency} for contact {contact.id} ({contact.whatsapp_id}). Status: {payment_status}")
            return payment, confirmation_action
    except Exception as e:
        logger.error(f"Failed to record payment for contact {contact.id} ({contact.whatsapp_id}). Error: {e}", exc_info=True)
        return None, None

def record_event_booking(
    contact: Contact,
    event_id: int,
    num_tickets: int = 1,
    status: str = 'confirmed',
    notes: str = None,
    proof_of_payment_wamid: str = None,
    event_fee: Decimal = None,
    event_title: str = None
) -> tuple:
    """
    Creates an EventBooking record for a contact.
    If the booking requires payment verification, it also creates a corresponding Payment record.
    Returns a tuple (EventBooking instance, context_updates dict).
    """
    try:
        event = Event.objects.get(pk=event_id)

        # If the booking is for a paid event and requires verification, create a payment record first.
        if status == 'pending_payment_verification' and event_fee and event_fee > 0:
            payment_obj, _ = record_payment(
                contact=contact,
                amount_str=str(event_fee),
                payment_type='event_registration',
                payment_method='manual_payment',
                status='pending_verification',
                notes=f"Payment for event: {event_title or event.title}",
                proof_of_payment_wamid=proof_of_payment_wamid
            )
            if not payment_obj:
                logger.error(f"Failed to create payment record for event booking for contact {contact.id} and event {event.id}.")
                return None, {'event_booking_success': False, 'event_booking_error': 'Could not create payment record.'}

        booking, created = EventBooking.objects.get_or_create(
            contact=contact,
            event=event,
            defaults={
                'number_of_tickets': num_tickets,
                'status': status,
                'notes': notes,
                'payment': payment_obj if 'payment_obj' in locals() else None
            }
        )

        if created:
            logger.info(f"Successfully created EventBooking {booking.id} for contact {contact.id} and event {event.id}.")
            context_updates = {'event_booking_success': True, 'last_booking_id': str(booking.id)}
        else:
            logger.warning(f"Contact {contact.id} is already booked for event {event.id}. Booking ID: {booking.id}.")
            context_updates = {'event_booking_success': False, 'event_booking_error': 'You are already registered for this event.'}
        
        return booking, context_updates

    except Event.DoesNotExist:
        logger.error(f"Failed to record booking for contact {contact.id}: Event with ID {event_id} not found.")
        return None, {'event_booking_success': False, 'event_booking_error': 'Event not found.'}
    except IntegrityError as e:
        logger.error(f"Database integrity error while booking event {event_id} for contact {contact.id}: {e}")
        return None, {'event_booking_success': False, 'event_booking_error': 'A database error occurred.'}
    except Exception as e:
        logger.error(f"Unexpected error recording event booking for contact {contact.id}: {e}", exc_info=True)
        return None, {'event_booking_success': False, 'event_booking_error': 'An unexpected error occurred.'}

def record_prayer_request(
    contact: Contact,
    request_text: str,
    category: str,
    is_anonymous: bool,
    submitted_as_member: bool = False
) -> PrayerRequest | None:
    """
    Creates a PrayerRequest record for a contact.

    Args:
        contact: The Contact object submitting the request.
        request_text: The text content of the prayer request.
        category: The category of the prayer request.
        is_anonymous: Boolean indicating if the request is anonymous.
        submitted_as_member: Boolean indicating if the user identified as a member.

    Returns:
        The created PrayerRequest object, or None if an error occurred.
    """
    if not request_text or not request_text.strip():
        logger.warning(f"Attempted to record an empty prayer request for contact {contact.id}. Aborting.")
        return None

    valid_categories = [choice[0] for choice in PrayerRequest.REQUEST_CATEGORY_CHOICES]
    if category not in valid_categories:
        logger.warning(f"Invalid prayer request category '{category}' for contact {contact.id}. Setting to 'other'.")
        category = 'other'

    try:
        with transaction.atomic():
            member_profile = MemberProfile.objects.filter(contact=contact).first()
            
            prayer_request = PrayerRequest.objects.create(
                contact=contact, member=member_profile, request_text=request_text,
                category=category, is_anonymous=is_anonymous,
                submitted_as_member=submitted_as_member, status='submitted'
            )
            logger.info(f"Successfully recorded prayer request {prayer_request.id} for contact {contact.id}.")
            return prayer_request
    except Exception as e:
        logger.error(f"Failed to record prayer request for contact {contact.id}. Error: {e}", exc_info=True)
        return None