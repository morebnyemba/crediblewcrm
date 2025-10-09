# whatsappcrm_backend/church_services/admin.py

from django.contrib import admin
from .models import Event, Ministry, Sermon, EventBooking

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin configuration for the Event model."""
    list_display = ('title', 'start_time', 'location', 'is_active', 'updated_at')
    search_fields = ('title', 'description', 'location')
    list_filter = ('is_active', 'start_time')
    ordering = ('-start_time',)
    list_per_page = 25

@admin.register(EventBooking)
class EventBookingAdmin(admin.ModelAdmin):
    """Admin configuration for the EventBooking model."""
    list_display = ('event', 'contact_name', 'status', 'booking_date')
    search_fields = ('event__title', 'contact__name', 'contact__whatsapp_id')
    list_filter = ('status', 'event')
    list_select_related = ('event', 'contact')
    readonly_fields = ('booking_date',)

@admin.register(Ministry)
class MinistryAdmin(admin.ModelAdmin):
    """Admin configuration for the Ministry model."""
    list_display = ('name', 'leader_name', 'is_active', 'updated_at')
    search_fields = ('name', 'leader_name', 'description')
    list_filter = ('is_active',)
    ordering = ('name',)

@admin.register(Sermon)
class SermonAdmin(admin.ModelAdmin):
    """Admin configuration for the Sermon model."""
    list_display = ('title', 'preacher', 'sermon_date', 'is_published', 'updated_at')
    search_fields = ('title', 'preacher', 'video_link')
    list_filter = ('is_published', 'preacher', 'sermon_date')
    ordering = ('-sermon_date',)
    list_per_page = 25