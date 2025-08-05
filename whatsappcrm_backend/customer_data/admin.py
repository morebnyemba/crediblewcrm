# whatsappcrm_backend/customer_data/admin.py

from django.contrib import admin
from .models import Family, MemberProfile, Payment, PaymentHistory, PrayerRequest, PendingVerificationPayment
from django.utils.html import format_html
from django.core.files.storage import default_storage
from django.utils import timezone
import logging

from conversations.models import Message
from meta_integration.models import MetaAppConfig
from meta_integration.tasks import send_whatsapp_message_task

logger = logging.getLogger(__name__)

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    """
    Admin interface for the Family model.
    """
    list_display = ('name', 'head_of_household', 'member_count', 'created_at')
    search_fields = ('name', 'head_of_household__name', 'head_of_household__whatsapp_id')
    list_per_page = 30

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'


class PaymentInline(admin.TabularInline):
    """
    Inline admin for displaying payments directly on the MemberProfile page.
    """
    model = Payment
    extra = 0
    fields = ('created_at', 'amount', 'currency', 'payment_type', 'status')
    readonly_fields = ('created_at',)
    show_change_link = True
    ordering = ('-created_at',)


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for the MemberProfile model.
    """
    list_display = ('get_full_name', 'contact', 'membership_status', 'city', 'family', 'updated_at')
    list_filter = ('membership_status', 'city', 'family', 'gender', 'marital_status')
    search_fields = ('first_name', 'last_name', 'email', 'contact__whatsapp_id', 'contact__name', 'city')
    readonly_fields = ('created_at', 'updated_at', 'last_updated_from_conversation')
    inlines = [PaymentInline]
    list_per_page = 25
    fieldsets = (
        ('Primary Info', {'fields': ('contact', ('first_name', 'last_name'), 'email')}),
        ('Personal Details', {'fields': ('date_of_birth', 'gender', 'marital_status')}),
        ('Church & Family', {'fields': ('family', 'membership_status', 'date_joined', 'baptism_date')}),
        ('Location', {'fields': ('address_line_1', 'address_line_2', 'city', 'country')}),
        ('Engagement', {'fields': ('acquisition_source', 'tags', 'notes')}),
        ('System Timestamps', {'fields': ('created_at', 'updated_at', 'last_updated_from_conversation'), 'classes': ('collapse',)}),
    )


class PaymentHistoryInline(admin.TabularInline):
    model = PaymentHistory
    extra = 0
    readonly_fields = ('timestamp', 'status', 'notes')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'member', 'contact', 'amount', 'currency', 'payment_type', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_type', 'currency', 'payment_method')
    search_fields = ('id', 'member__first_name', 'member__last_name', 'contact__whatsapp_id', 'transaction_reference')
    readonly_fields = ('id', 'created_at', 'updated_at', 'display_proof_of_payment')
    inlines = [PaymentHistoryInline]
    list_per_page = 30
    fieldsets = (
        ('Transaction Details', {'fields': ('id', 'status', 'amount', 'currency', 'payment_type', 'payment_method')}),
        ('Associated Parties', {'fields': ('member', 'contact')}),
        ('References & Proof', {'fields': ('transaction_reference', 'display_proof_of_payment', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def display_proof_of_payment(self, obj):
        """
        Displays the proof of payment image as a clickable thumbnail in the admin.
        The URL is generated dynamically from the stored path.
        """
        if obj.proof_of_payment: # Check if the ImageField has a file
            try:
                # Access the .url attribute directly from the ImageField
                return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 200px; max-height: 200px;" /></a>', obj.proof_of_payment.url)
            except Exception:
                return "Error: Image file not found in storage."
        return "No proof uploaded."
    display_proof_of_payment.short_description = 'Proof of Payment'


@admin.register(PendingVerificationPayment)
class PendingVerificationPaymentAdmin(admin.ModelAdmin):
    """
    Admin view specifically for verifying manual payments that are in 'pending_verification' status.
    """
    list_display = ('id', 'member', 'contact', 'amount', 'currency', 'payment_type', 'created_at', 'display_proof_of_payment_thumbnail')
    list_filter = ('payment_type', 'currency')
    search_fields = ('id', 'member__first_name', 'member__last_name', 'contact__whatsapp_id')
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'display_proof_of_payment', 'member', 'contact',
        'amount', 'currency', 'payment_type', 'payment_method', 'notes', 'status'
    )
    actions = ['approve_selected_payments', 'deny_selected_payments']
    list_per_page = 25

    def get_queryset(self, request):
        # Filter to only show payments pending verification
        return super().get_queryset(request).filter(status='pending_verification')

    def display_proof_of_payment(self, obj):
        """Displays the proof of payment image as a large, clickable thumbnail in the detail view. Prevents errors from missing files"""
        if obj.proof_of_payment: # Check if the ImageField has a file
            try:
                # Access the .url attribute directly from the ImageField
                return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 400px; max-height: 400px;" /></a>', obj.proof_of_payment.url)
            except Exception:
                return "Error retrieving image."
        return "No proof uploaded."
    display_proof_of_payment.short_description = 'Proof of Payment'


    def display_proof_of_payment_thumbnail(self, obj):
        """Displays a smaller thumbnail for the list view."""
        if obj.proof_of_payment: # Check if the ImageField has a file
            try:
                # Access the .url attribute directly from the ImageField
                return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 80px; max-height: 80px;" /></a>', obj.proof_of_payment.url)
            except Exception:
                return "Error" # Keep it short for the list view
        return "No proof."
    display_proof_of_payment_thumbnail.short_description = 'Proof Thumbnail'

    def _send_status_notification(self, payment: Payment, active_config: MetaAppConfig, message_text: str) -> bool:
        """Helper to create and dispatch a WhatsApp notification for a payment status change."""
        if not payment.contact:
            logger.warning(f"Payment {payment.id} has no associated contact. Cannot send notification.")
            return False

        try:
            message = Message.objects.create(
                contact=payment.contact,
                app_config=active_config,
                direction='out',
                message_type='text',
                content_payload={'body': message_text},
                status='pending_dispatch',
                timestamp=timezone.now()
            )
            send_whatsapp_message_task.delay(message.id, active_config.id)
            logger.info(f"Queued status notification for payment {payment.id} to contact {payment.contact.id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to create and dispatch notification for payment {payment.id}. Error: {e}", exc_info=True)
            return False

    @admin.action(description='Approve selected payments (Mark as Completed)')
    def approve_selected_payments(self, request, queryset):
        """Admin action to approve payments, setting status to 'completed' and adding a note."""
        try:
            active_config = MetaAppConfig.objects.get_active_config()
        except (MetaAppConfig.DoesNotExist, MetaAppConfig.MultipleObjectsReturned) as e:
            self.message_user(request, f"Action completed, but could not send notifications: {e}", level='warning')
            active_config = None

        approved_count = 0
        notified_count = 0
        for payment in queryset:
            payment.status = 'completed'
            note = f"Payment approved by admin user '{request.user.username}' on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}."
            payment.notes = f"{payment.notes}\n{note}" if payment.notes else note
            payment.save(update_fields=['status', 'notes', 'updated_at'])
            approved_count += 1

            if active_config and payment.contact:
                message_text = (
                    f"Hello {payment.contact.name or 'member'},\n\n"
                    f"Your payment of *{payment.amount} {payment.currency}* for *{payment.get_payment_type_display()}* has been approved. "
                    "Thank you for your contribution! 🙏"
                )
                if self._send_status_notification(payment, active_config, message_text):
                    notified_count += 1
        
        message = f'{approved_count} payments were successfully marked as completed.'
        if active_config:
            message += f' {notified_count} notifications were queued for sending.'
        self.message_user(request, message)

    @admin.action(description='Deny selected payments (Mark as Failed)')
    def deny_selected_payments(self, request, queryset):
        """Admin action to deny payments, setting status to 'failed' and adding a note."""
        try:
            active_config = MetaAppConfig.objects.get_active_config()
        except (MetaAppConfig.DoesNotExist, MetaAppConfig.MultipleObjectsReturned) as e:
            self.message_user(request, f"Action completed, but could not send notifications: {e}", level='warning')
            active_config = None

        denied_count = 0
        notified_count = 0
        for payment in queryset:
            payment.status = 'failed'
            note = f"Payment denied by admin user '{request.user.username}' on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}."
            payment.notes = f"{payment.notes}\n{note}" if payment.notes else note
            payment.save(update_fields=['status', 'notes', 'updated_at'])
            denied_count += 1

            if active_config and payment.contact:
                message_text = (
                    f"Hello {payment.contact.name or 'member'},\n\n"
                    f"There was an issue regarding your recent payment of *{payment.amount} {payment.currency}* for *{payment.get_payment_type_display()}*. "
                    "Please contact the church office for assistance."
                )
                if self._send_status_notification(payment, active_config, message_text):
                    notified_count += 1
        
        message = f'{denied_count} payments were successfully denied and marked as failed.'
        if active_config:
            message += f' {notified_count} notifications were queued for sending.'
        self.message_user(request, message)

    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('payment', 'status', 'timestamp', 'notes')
    list_filter = ('status',)
    search_fields = ('payment__id',)
    readonly_fields = ('payment', 'status', 'timestamp', 'notes')


@admin.register(PrayerRequest)
class PrayerRequestAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'contact', 'category', 'status', 'is_anonymous', 'created_at')
    list_filter = ('status', 'category', 'is_anonymous', 'created_at')
    search_fields = ('request_text', 'contact__whatsapp_id', 'member__first_name', 'member__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_per_page = 30
    fieldsets = (
        ('Request Details', {'fields': ('id', 'status', 'category', 'request_text')}),
        ('Submitter', {'fields': ('contact', 'member', 'is_anonymous')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )