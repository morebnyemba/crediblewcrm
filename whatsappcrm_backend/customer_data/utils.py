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
) -> Payment | None:
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
        The created Payment object, or None if an error occurred.
    """
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            logger.warning(f"Attempted to record a non-positive payment amount ({amount}) for contact {contact.id}. Aborting.")
            return None
    except (InvalidOperation, TypeError):
        logger.error(f"Invalid amount '{amount_str}' provided for payment for contact {contact.id}. Cannot convert to Decimal.")
        return None

    valid_payment_types = [choice[0] for choice in Payment.PAYMENT_TYPE_CHOICES]
    if payment_type not in valid_payment_types:
        logger.warning(f"Invalid payment_type '{payment_type}' for contact {contact.id}. Defaulting to 'other'.")
        payment_type = 'other'

    try:
        with transaction.atomic():
            member_profile = MemberProfile.objects.filter(contact=contact).first()

            payment = Payment.objects.create(
                contact=contact, member=member_profile, amount=amount, currency=currency,
                payment_type=payment_type, payment_method=payment_method,
                status='completed', transaction_reference=transaction_ref, notes=notes
            )

            PaymentHistory.objects.create(payment=payment, status='completed', notes=f"Payment recorded via flow for contact {contact.whatsapp_id}.")
            logger.info(f"Successfully recorded payment {payment.id} of {amount} {currency} for contact {contact.id}.")
            return payment
    except Exception as e:
        logger.error(f"Failed to record payment for contact {contact.id}. Error: {e}", exc_info=True)
        return None