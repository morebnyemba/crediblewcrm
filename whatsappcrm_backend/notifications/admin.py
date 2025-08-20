# whatsappcrm_backend/notifications/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'channel', 'status', 'related_contact_link', 'created_at', 'sent_at')
    list_filter = ('status', 'channel', 'created_at', 'recipient')
    search_fields = ('recipient__username', 'content', 'related_contact__name', 'related_contact__whatsapp_id')
    readonly_fields = ('recipient', 'channel', 'status', 'content', 'related_contact', 'related_flow', 'created_at', 'sent_at', 'error_message')
    list_select_related = ('recipient', 'related_contact')

    def related_contact_link(self, obj):
        if obj.related_contact:
            link = reverse("admin:conversations_contact_change", args=[obj.related_contact.id])
            return format_html('<a href="{}">{}</a>', link, obj.related_contact)
        return "N/A"
    related_contact_link.short_description = "Related Contact"

    def has_add_permission(self, request):
        # Notifications are created by the system, not manually in the admin
        return False

    def has_change_permission(self, request, obj=None):
        # Notification logs are immutable records
        return False