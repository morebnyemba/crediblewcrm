# whatsappcrm_backend/notifications/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Notification(models.Model):
    """
    Represents a single notification sent to a system user. This provides a
    log and allows for status tracking.
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('failed', _('Failed')),
    ]
    CHANNEL_CHOICES = [
        ('whatsapp', _('WhatsApp')),
        ('email', _('Email')),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=_("The system user who received the notification.")
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='whatsapp')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    content = models.TextField(help_text=_("The body of the notification message."))
    
    related_contact = models.ForeignKey(
        'conversations.Contact', on_delete=models.SET_NULL, null=True, blank=True,
        help_text=_("The contact that this notification is about, if any.")
    )
    related_flow = models.ForeignKey(
        'flows.Flow', on_delete=models.SET_NULL, null=True, blank=True,
        help_text=_("The flow that triggered this notification, if any.")
    )
    
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Notification to {self.recipient.username} via {self.channel} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Notification Log")
        verbose_name_plural = _("Notification Logs")