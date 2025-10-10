from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Leave blank for free events.")
    is_active = models.BooleanField(default=True, help_text="Whether the event is publicly visible.")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Optional: Latitude for the event location.")
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True, help_text="Optional: Longitude for the event location.")
    flyer = models.ImageField(upload_to='event_flyers/%Y/%m/', blank=True, null=True, help_text="Optional flyer or picture for the event.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['start_time']
        verbose_name = _("Event")
        verbose_name_plural = _("Events")

class EventBooking(models.Model):
    """Represents a booking made by a contact for a specific event."""
    BOOKING_SOURCE_CHOICES = [
        ('whatsapp_flow', _('WhatsApp Flow')),
        ('admin_panel', _('Admin Panel')),
        ('web_form', _('Web Form')),
        ('other', _('Other')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=20, unique=True, editable=False, blank=True, null=True, help_text="Unique, human-readable reference for the booking.")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    contact = models.ForeignKey('conversations.Contact', on_delete=models.CASCADE, related_name='event_bookings')
    payment = models.OneToOneField(
        'customer_data.Payment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='event_booking', help_text="Link to the payment record for this booking, if applicable.")
    booking_date = models.DateTimeField(auto_now_add=True)
    booking_source = models.CharField(
        max_length=20,
        choices=BOOKING_SOURCE_CHOICES,
        default='whatsapp_flow',
        help_text="How this booking was created."
    )
    status = models.CharField(
        max_length=30,
        choices=[
            ('confirmed', 'Confirmed'),
            ('pending_payment_verification', 'Pending Payment Verification'),
            ('cancelled', 'Cancelled'),
            ('attended', 'Attended')
        ],
        default='confirmed'
    )
    check_in_time = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp of when the contact was checked in at the event."
    )
    notes = models.TextField(blank=True, null=True, help_text="Internal notes about the booking.")

    def clean(self):
        super().clean()
        # Prevent booking for events that have already started, unless it's an admin override.
        if self.event and self.event.start_time < timezone.now() and self.booking_source != 'admin_panel':
            raise models.ValidationError(_("Bookings cannot be made for events that have already started."))

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            # Generate a unique reference, e.g., EVT-2024-0001
            today = timezone.now().date()
            year = today.year
            last_booking = EventBooking.objects.filter(booking_reference__startswith=f'EVT-{year}-').order_by('booking_reference').last()
            if last_booking and last_booking.booking_reference:
                last_num = int(last_booking.booking_reference.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.booking_reference = f'EVT-{year}-{new_num:04d}'
        
        self.full_clean() # Run validation before saving
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-booking_date']
        unique_together = [['event', 'contact']] # A contact can only book an event once
        verbose_name = _("Event Booking")
        verbose_name_plural = _("Event Bookings")

    def __str__(self):
        return f"Booking ({self.booking_reference or 'N/A'}) for {self.contact} at {self.event.title}"

class Ministry(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField()
    leader_name = models.CharField(max_length=150, blank=True)
    contact_info = models.CharField(max_length=150, blank=True, help_text="e.g., Phone number or email")
    meeting_schedule = models.CharField(max_length=255, blank=True, help_text="e.g., 'Tuesdays at 7 PM in the main hall'")
    is_active = models.BooleanField(default=True, help_text="Whether the ministry is currently active and listed.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Ministry")
        verbose_name_plural = _("Ministries")

class Sermon(models.Model):
    title = models.CharField(max_length=200)
    preacher = models.CharField(max_length=150)
    sermon_date = models.DateField()
    video_link = models.URLField(max_length=500, blank=True, help_text="Link to YouTube, Vimeo, etc.")
    audio_link = models.URLField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False, help_text="Make this sermon visible to the public.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.preacher}"

    class Meta:
        ordering = ['-sermon_date']
        verbose_name = _("Sermon")
        verbose_name_plural = _("Sermons")
