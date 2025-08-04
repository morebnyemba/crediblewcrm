# whatsappcrm_backend/customer_data/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
# Link to the Contact model from the conversations app
from conversations.models import Contact
import uuid

class Family(models.Model):
    """
    Represents a family unit to group members together.
    """
    name = models.CharField(_("Family Name"), max_length=150, help_text=_("e.g., 'The Smith Family'"))
    head_of_household = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_families',
        help_text=_("The primary contact for this family unit.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Family")
        verbose_name_plural = _("Families")
        ordering = ['name']

class MemberProfile(models.Model):
    """
    Stores aggregated and specific data about a church member, linked to their Contact record.
    This profile is enriched over time through conversations, forms, and flow interactions.
    """
    contact = models.OneToOneField(
        Contact,
        on_delete=models.CASCADE,
        related_name='member_profile',
        primary_key=True, # Makes contact_id the primary key for this table
        help_text=_("The contact this member profile belongs to.")
    )
    
    # Personal Details
    first_name = models.CharField(_("First Name"), max_length=100, blank=True, null=True)
    last_name = models.CharField(_("Last Name"), max_length=100, blank=True, null=True)
    email = models.EmailField(_("Email Address"), max_length=254, blank=True, null=True)
    secondary_phone_number = models.CharField(_("Secondary Phone"), max_length=30, blank=True, null=True, help_text=_("An alternative phone number, if provided."))
    date_of_birth = models.DateField(_("Date of Birth"), null=True, blank=True)
    
    GENDER_CHOICES = [
        ('male', _('Male')),
        ('female', _('Female')),
        ('other', _('Other')),
        ('prefer_not_to_say', _('Prefer not to say')),
    ]
    gender = models.CharField(_("Gender"), max_length=20, choices=GENDER_CHOICES, blank=True, null=True)

    MARITAL_STATUS_CHOICES = [
        ('single', _('Single')),
        ('married', _('Married')),
        ('divorced', _('Divorced')),
        ('widowed', _('Widowed')),
    ]
    marital_status = models.CharField(_("Marital Status"), max_length=20, choices=MARITAL_STATUS_CHOICES, blank=True, null=True)

    # Family & Church Details
    family = models.ForeignKey(
        Family,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        help_text=_("The family unit this member belongs to.")
    )
    date_joined = models.DateField(_("Date Joined"), null=True, blank=True, help_text=_("The date the person officially joined the church."))
    baptism_date = models.DateField(_("Baptism Date"), null=True, blank=True)

    # Location Details
    address_line_1 = models.CharField(_("Address Line 1"), max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(_("Address Line 2"), max_length=255, blank=True, null=True)
    city = models.CharField(_("City"), max_length=100, blank=True, null=True)
    state_province = models.CharField(_("State/Province"), max_length=100, blank=True, null=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True, null=True)
    country = models.CharField(_("Country"), max_length=100, blank=True, null=True)

    # Church Engagement Specifics
    MEMBERSHIP_STATUS_CHOICES = [
        ('visitor', _('Visitor')),
        ('new_convert', _('New Convert')),
        ('member', _('Member')),
        ('leader', _('Leader')),
        ('inactive', _('Inactive')),
        ('other', _('Other')),
    ]
    membership_status = models.CharField(
        _("Membership Status"),
        max_length=50,
        choices=MEMBERSHIP_STATUS_CHOICES,
        blank=True,
        null=True,
        default='visitor'
    )
    acquisition_source = models.CharField(
        _("Acquisition Source"),
        max_length=150, 
        blank=True, 
        null=True, 
        help_text=_("How this person was reached, e.g., 'Outreach Event', 'Website', 'Referral'")
    )
    tags = models.JSONField( # List of strings
        _("Tags"),
        default=list, 
        blank=True, 
        help_text=_("Descriptive tags for segmentation, e.g., ['youth_ministry', 'choir', 'volunteer']")
    )
    notes = models.TextField(
        _("Notes"), 
        blank=True, 
        null=True,
        help_text=_("General notes about the member, prayer requests, etc.")
    )

    # Flexible JSON fields for data collected via flows or integrations
    preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Member preferences collected over time (e.g., communication preference, service time).")
    )
    custom_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Arbitrary custom attributes collected for this member.")
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, help_text=_("Last time this profile record was updated."))
    last_updated_from_conversation = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text=_("Last time data was explicitly updated from a conversation or flow.")
    )

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return None

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"Member Profile for {full_name} ({self.contact.whatsapp_id})"
        return f"Member Profile for {self.contact.name or self.contact.whatsapp_id}"

    class Meta:
        verbose_name = _("Member Profile")
        verbose_name_plural = _("Member Profiles")
        ordering = ['-updated_at']

class Payment(models.Model):
    """
    Represents a single payment transaction, linked to a member and/or contact.
    """
    PAYMENT_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('pending_verification', _('Pending Verification')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('refunded', _('Refunded')),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('ecocash', _('EcoCash')),
        ('manual_payment', _('Manual/Cash Payment')),
        ('omari', _('Omari (Coming Soon)')),
        ('innbucks', _('Innbucks (Coming Soon)')),
    ]
    PAYMENT_TYPE_CHOICES = [
        ('tithe', _('Tithe')),
        ('offering', _('Offering')),
        ('pledge', 'Pledge'),
        ('event_registration', _('Event Registration')),
        ('other', _('Other')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments',
        help_text=_("The member profile associated with this payment, if one exists.")
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='initiated_payments',
        help_text=_("The contact who initiated the payment, even if not a full member.")
    )
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
    currency = models.CharField(_("Currency"), max_length=10, default='USD')
    payment_type = models.CharField(_("Payment Type"), max_length=50, choices=PAYMENT_TYPE_CHOICES, default='offering')
    payment_method = models.CharField(_("Payment Method"), max_length=50, choices=PAYMENT_METHOD_CHOICES, blank=True)
    status = models.CharField(_("Status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_reference = models.CharField(_("Transaction Reference"), max_length=255, blank=True, null=True, help_text="Reference from payment gateway or bank.")
    external_data = models.JSONField(
        _("External Data"),
        default=dict,
        blank=True,
        help_text=_("Data from external payment gateways, like Paynow poll_url or reference.")
    )
    notes = models.TextField(_("Notes"), blank=True, null=True, help_text="Internal notes about the payment.")
    proof_of_payment_url = models.URLField(
        _("Proof of Payment URL"),
        max_length=1024,
        blank=True,
        null=True,
        help_text=_("URL of the image uploaded as proof for manual or cash payments.")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to automatically create a PaymentHistory
        record on creation or on status change.
        """
        # Check if the object is new or if the status has changed.
        is_new = self._state.adding
        status_changed = False

        if not is_new:
            try:
                old_obj = Payment.objects.get(pk=self.pk)
                if old_obj.status != self.status:
                    status_changed = True
            except Payment.DoesNotExist:
                # This case is unlikely but good to handle. Treat as new.
                status_changed = True

        # Call the original save method first.
        super().save(*args, **kwargs)

        # If it's a new payment or the status changed, create a history record.
        if is_new or status_changed:
            PaymentHistory.objects.create(payment=self, status=self.status)

    def __str__(self):
        display_name = self.member.get_full_name() if self.member and self.member.get_full_name() else str(self.contact)
        return f"Payment {self.id} - {self.amount} {self.currency} by {display_name}"

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ['-created_at']

class PaymentHistory(models.Model):
    """
    Logs the status changes for a Payment, creating an audit trail.
    """
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Payment.PAYMENT_STATUS_CHOICES,
        help_text=_("The status of the payment at this point in time.")
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(_("Notes"), blank=True, null=True, help_text="Reason for the status change, if any.")

    def __str__(self):
        return f"History for Payment {self.payment.id}: {self.status} at {self.timestamp}"

    class Meta:
        verbose_name = _("Payment History")
        verbose_name_plural = _("Payment Histories")
        ordering = ['-timestamp']

class PrayerRequest(models.Model):
    """
    Stores a prayer request submitted by a member or contact.
    """
    REQUEST_CATEGORY_CHOICES = [
        ('healing', _('Healing')),
        ('family', _('Family & Relationships')),
        ('guidance', _('Guidance & Wisdom')),
        ('thanksgiving', _('Thanksgiving')),
        ('financial', _('Financial Provision')),
        ('other', _('Other')),
    ]
    STATUS_CHOICES = [
        ('submitted', _('Submitted')),
        ('in_prayer', _('In Prayer')),
        ('answered', _('Answered')),
        ('closed', _('Closed')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prayer_requests',
        help_text=_("The member profile associated with this prayer request, if available.")
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='prayer_requests',
        help_text=_("The contact who submitted the prayer request.")
    )
    request_text = models.TextField(_("Prayer Request"), help_text=_("The content of the prayer request."))
    category = models.CharField(
        _("Category"), max_length=50, choices=REQUEST_CATEGORY_CHOICES, blank=True, null=True
    )
    is_anonymous = models.BooleanField(
        _("Submit Anonymously"),
        default=False,
        help_text=_("If true, the submitter's name will not be shared publicly.")
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default='submitted'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        submitter = "Anonymous" if self.is_anonymous else (self.member.get_full_name() if self.member and self.member.get_full_name() else str(self.contact))
        return f"Prayer Request from {submitter} ({self.get_category_display() or 'General'})"

    class Meta:
        verbose_name = _("Prayer Request")
        verbose_name_plural = _("Prayer Requests")
        ordering = ['-created_at']
