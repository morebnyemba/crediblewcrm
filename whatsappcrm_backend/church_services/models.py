from django.db import models
from django.utils.translation import gettext_lazy as _

class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, help_text="Whether the event is publicly visible.")
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
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    contact = models.ForeignKey('conversations.Contact', on_delete=models.CASCADE, related_name='event_bookings')
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('confirmed', 'Confirmed'), ('cancelled', 'Cancelled'), ('attended', 'Attended')],
        default='confirmed'
    )
    notes = models.TextField(blank=True, null=True, help_text="Internal notes about the booking.")

    class Meta:
        ordering = ['-booking_date']
        unique_together = [['event', 'contact']] # A contact can only book an event once
        verbose_name = _("Event Booking")
        verbose_name_plural = _("Event Bookings")

    def __str__(self):
        return f"Booking for {self.contact} at {self.event.title}"

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
