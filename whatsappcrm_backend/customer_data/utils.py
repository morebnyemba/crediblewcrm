# whatsappcrm_backend/customer_data/utils.py

import logging
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone

from conversations.models import Contact
from .models import MemberProfile, Payment, PaymentHistory

logger = logging.getLogger(__name__)

def record_payment(
    contact: Contact,
    amount_str: str,
    payment_type: str,
    currency: str = 'USD',
    payment_method: str = 'whatsapp_flow',
    transaction_ref: str = None,
    notes: str = None
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

    Returns:
        A tuple of (Payment object, confirmation_action_dict), or (None, None) if an error occurred.
    """
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            logger.warning(f"Attempted to record a non-positive payment amount ({amount}) for contact {contact.id}. Aborting.")
            return None, None
    except (InvalidOperation, TypeError):
        logger.error(f"Invalid amount '{amount_str}' provided for payment for contact {contact.id}. Cannot convert to Decimal.")
        return None, None

    valid_payment_types = [choice[0] for choice in Payment.PAYMENT_TYPE_CHOICES]
    if payment_type not in valid_payment_types:
        logger.warning(f"Invalid payment_type '{payment_type}' for contact {contact.id}. Defaulting to 'other'.")
        payment_type = 'other'

    try:
        with transaction.atomic():
            member_profile = MemberProfile.objects.filter(contact=contact).first()

            # Determine status and confirmation message based on payment method
            is_manual_payment = payment_method == 'manual_payment'
            payment_status = 'pending' if is_manual_payment else 'completed'

            payment = Payment.objects.create(
                contact=contact, member=member_profile, amount=amount, currency=currency,
                payment_type=payment_type, payment_method=payment_method,
                status=payment_status, transaction_reference=transaction_ref, notes=notes
            )

            history_note = f"Payment recorded via flow for contact {contact.whatsapp_id}."
            if is_manual_payment:
                history_note = f"Manual payment initiated via flow for contact {contact.whatsapp_id}. Awaiting confirmation."

            PaymentHistory.objects.create(payment=payment, status=payment_status, notes=history_note)
            
            # Create confirmation message action
            if is_manual_payment:
                ref_text = f" using reference: *{transaction_ref}*" if transaction_ref else ""
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
            
            confirmation_action = {
                'type': 'send_whatsapp_message',
                'recipient_wa_id': contact.whatsapp_id,
                'message_type': 'text',
                'data': {'body': confirmation_message_text}
            }

            logger.info(f"Successfully recorded payment {payment.id} of {amount} {currency} for contact {contact.id}. Status: {payment_status}")
            return payment, confirmation_action
    except Exception as e:
        logger.error(f"Failed to record payment for contact {contact.id}. Error: {e}", exc_info=True)
        return None, None