# whatsappcrm_backend/customer_data/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
# Link to the Contact model from the conversations app
from conversations.models import Contact

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
