# whatsappcrm_backend/church_services/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Event, Ministry, Sermon, EventBooking

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin configuration for the Event model."""
    list_display = ('title', 'start_time', 'location', 'is_active', 'has_location_pin', 'display_flyer_thumbnail', 'updated_at')
    search_fields = ('title', 'description', 'location')
    list_filter = ('is_active', 'start_time')
    ordering = ('-start_time',)
    list_per_page = 25
    readonly_fields = ('display_flyer', 'location_map_link', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('title', 'description', 'is_active', 'registration_fee')}),
        ('Date & Time', {'fields': ('start_time', 'end_time')}),
        ('Location', {'fields': ('location', ('latitude', 'longitude'), 'location_map_link')}),
        ('Media', {'fields': ('flyer', 'display_flyer')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def display_flyer_thumbnail(self, obj):
        if obj.flyer:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 80px; max-height: 80px;" /></a>', obj.flyer.url)
        return "No Flyer"
    display_flyer_thumbnail.short_description = 'Flyer'

    def display_flyer(self, obj):
        """Displays a larger preview of the flyer in the detail view."""
        if obj.flyer:
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 400px; max-height: 400px;" /></a>', obj.flyer.url)
        return "No Flyer"
    display_flyer.short_description = 'Flyer Preview'

    def has_location_pin(self, obj):
        return bool(obj.latitude and obj.longitude)
    has_location_pin.boolean = True
    has_location_pin.short_description = 'Has Pin'

    def location_map_link(self, obj):
        if obj.latitude and obj.longitude:
            return format_html('<a href="https://www.google.com/maps/search/?api=1&query={0},{1}" target="_blank">View on Google Maps</a>', obj.latitude, obj.longitude)
        return "N/A"
    location_map_link.short_description = 'Map Link'

@admin.register(EventBooking)
class EventBookingAdmin(admin.ModelAdmin):
    """Admin configuration for the EventBooking model."""
    list_display = ('booking_reference', 'event', 'contact_name', 'number_of_tickets', 'status', 'booking_source', 'booking_date')
    search_fields = ('booking_reference', 'event__title', 'contact__name', 'contact__whatsapp_id')
    list_filter = ('status', 'event', 'booking_source')
    list_select_related = ('event', 'contact')
    readonly_fields = ('id', 'booking_reference', 'booking_date', 'check_in_time')

    def contact_name(self, obj):
        """Returns the contact's name or WhatsApp ID for display."""
        if obj.contact:
            return obj.contact.name or obj.contact.whatsapp_id
        return "N/A"
    contact_name.short_description = 'Contact Name'

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