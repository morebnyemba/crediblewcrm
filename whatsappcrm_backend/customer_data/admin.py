# whatsappcrm_backend/customer_data/admin.py

from django.contrib import admin
from .models import Family, MemberProfile, Payment, PaymentHistory, PrayerRequest, PendingVerificationPayment
from django.utils.html import format_html
from django.core.files.storage import default_storage
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.db import transaction
import logging

from conversations.models import Message
from meta_integration.models import MetaAppConfig
from meta_integration.tasks import send_whatsapp_message_task
from church_services.models import EventBooking
from .exports import (
    export_members_to_excel, export_members_to_pdf,
    export_payment_summary_to_excel, export_payment_summary_to_pdf,
    export_givers_list_finance_excel, export_givers_list_finance_pdf,
    export_givers_list_publication_excel, export_givers_list_publication_pdf
)


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
    actions = ['export_all_members_to_excel', 'export_all_members_to_pdf']
    fieldsets = (
        ('Primary Info', {'fields': ('contact', ('first_name', 'last_name'), 'email')}),
        ('Personal Details', {'fields': ('date_of_birth', 'gender', 'marital_status')}),
        ('Church & Family', {'fields': ('family', 'membership_status', 'date_joined', 'baptism_date')}),
        ('Location', {'fields': ('address_line_1', 'address_line_2', 'city', 'country')}),
        ('Engagement', {'fields': ('acquisition_source', 'tags', 'notes')}),
        ('System Timestamps', {'fields': ('created_at', 'updated_at', 'last_updated_from_conversation'), 'classes': ('collapse',)}),
    )

    @admin.action(description='Export ALL members to Excel')
    def export_all_members_to_excel(self, request, queryset):
        all_members = MemberProfile.objects.all()
        return export_members_to_excel(all_members)

    @admin.action(description='Export ALL members to PDF')
    def export_all_members_to_pdf(self, request, queryset):
        all_members = MemberProfile.objects.all()
        return export_members_to_pdf(all_members)

    
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
    actions = [
        'export_summary_week_excel', 'export_summary_week_pdf',
        'export_summary_month_excel', 'export_summary_month_pdf',
        'export_summary_year_excel', 'export_summary_year_pdf',
        'export_givers_finance_month_excel',
        'export_givers_finance_month_pdf',
        'export_givers_publication_month_excel',
        'export_givers_publication_month_pdf',
    ]
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

    @admin.action(description='Export weekly payment summary (Excel)')
    def export_summary_week_excel(self, request, queryset):
        now = timezone.now()
        start_date = now - timedelta(days=7)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_payment_summary_to_excel(payments, 'last_7_days')

    @admin.action(description='Export weekly payment summary (PDF)')
    def export_summary_week_pdf(self, request, queryset):
        now = timezone.now()
        start_date = now - timedelta(days=7)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_payment_summary_to_pdf(payments, 'last_7_days')

    @admin.action(description='Export monthly payment summary (Excel)')
    def export_summary_month_excel(self, request, queryset):
        now = timezone.now()
        start_date = now - timedelta(days=30)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_payment_summary_to_excel(payments, 'last_30_days')

    @admin.action(description='Export monthly payment summary (PDF)')
    def export_summary_month_pdf(self, request, queryset):
        now = timezone.now()
        start_date = now - timedelta(days=30)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_payment_summary_to_pdf(payments, 'last_30_days')

    @admin.action(description='Export yearly payment summary (Excel)')
    def export_summary_year_excel(self, request, queryset):
        now = timezone.now()
        start_date = now - timedelta(days=365)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_payment_summary_to_excel(payments, 'last_365_days')

    @admin.action(description='Export yearly payment summary (PDF)')
    def export_summary_year_pdf(self, request, queryset):
        now = timezone.now()
        start_date = now - timedelta(days=365)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_payment_summary_to_pdf(payments, 'last_365_days')

    @admin.action(description='Export monthly givers list for Finance (Excel)')
    def export_givers_finance_month_excel(self, request, queryset):
        now = timezone.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_givers_list_finance_excel(payments, 'current_month')

    @admin.action(description='Export monthly givers list for Finance (PDF)')
    def export_givers_finance_month_pdf(self, request, queryset):
        now = timezone.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_givers_list_finance_pdf(payments, 'current_month')

    @admin.action(description='Export monthly givers list for Publication (Excel)')
    def export_givers_publication_month_excel(self, request, queryset):
        now = timezone.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_givers_list_publication_excel(payments, 'current_month')

    @admin.action(description='Export monthly givers list for Publication (PDF)')
    def export_givers_publication_month_pdf(self, request, queryset):
        now = timezone.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        payments = Payment.objects.filter(created_at__gte=start_date, status='completed')
        return export_givers_list_publication_pdf(payments, 'current_month')



@admin.register(PendingVerificationPayment)
class PendingVerificationPaymentAdmin(admin.ModelAdmin):
    """
    Admin view specifically for verifying manual payments that are in 'pending_verification' status.
    """
    list_display = ('id', 'member', 'contact', 'amount', 'currency', 'payment_type', 'created_at', 'updated_at', 'display_proof_of_payment_thumbnail')
    list_filter = ('payment_type', 'currency')
    search_fields = ('id', 'member__first_name', 'member__last_name', 'contact__whatsapp_id')
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'display_proof_of_payment', 'member', 'contact',
        'amount', 'currency', 'payment_type', 'payment_method', 'notes', 'status'
    )
    actions = ['approve_selected_payments', 'deny_selected_payments']
    list_per_page = 25
    ordering = ('-updated_at',) # Order by most recently updated, so oldest pending are first

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
            transaction.on_commit(
                lambda: send_whatsapp_message_task.delay(message.id, active_config.id)
            )
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
                full_name = payment.member.get_full_name() if payment.member and payment.member.get_full_name() else payment.contact.name
                recipient_name = full_name or 'church member'

                message_text = (
                    f"Dear {recipient_name},\n\n"
                    f"Praise God! We confirm with thanks the receipt of your *{payment.get_payment_type_display()}* of *{payment.amount} {payment.currency}*.\n\n"
                    "Your faithfulness and generosity are a blessing to the ministry. We pray for God's abundant blessings upon you and your family.\n\n"
                    "\"Each of you should give what you have decided in your heart to give, not reluctantly or under compulsion, for God loves a cheerful giver.\" - 2 Corinthians 9:7\n\n"
                    "In His Grace,\n"
                    "The Church Accounts Team"
                )
                if self._send_status_notification(payment, active_config, message_text):
                    notified_count += 1
        
            # --- New Logic: Check for and update related EventBooking ---
            try:
                # The related_name from EventBooking's OneToOneField to Payment is 'event_booking'
                booking = payment.event_booking
                if booking and booking.status == 'pending_payment_verification':
                    booking.status = 'confirmed'
                    booking.save(update_fields=['status'])
                    logger.info(f"Updated EventBooking {booking.id} to 'confirmed' for approved payment {payment.id}.")

                    # Send a specific notification for the event booking confirmation
                    if active_config and booking.contact:
                        recipient_name = booking.contact.name or 'church member'
                        event_title = booking.event.title if booking.event else "the event"
                        booking_confirmation_message = (
                            f"🎉 Great news, {recipient_name}!\n\n"
                            f"Your payment has been confirmed, and you are now officially registered for *{event_title}*.\n\n"
                            "We can't wait to see you there! Get ready for a blessed time.\n\n"
                            "In His Grace,\n"
                            "The Events Team"
                        )
                        # We can reuse the _send_status_notification helper, but we need to adapt it
                        # to take a contact and message directly, or create a new one.
                        # For now, let's create a new message and task.
                        booking_message = Message.objects.create(
                            contact=booking.contact, app_config=active_config, direction='out',
                            message_type='text', content_payload={'body': booking_confirmation_message},
                            status='pending_dispatch', timestamp=timezone.now()
                        )
                        transaction.on_commit(lambda: send_whatsapp_message_task.delay(booking_message.id, active_config.id))
            except EventBooking.DoesNotExist:
                # This is expected for payments not related to an event booking.
                pass
            except Exception as e:
                logger.error(f"Error updating related event booking for payment {payment.id}: {e}", exc_info=True)
                self.message_user(request, f"Payment {payment.id} approved, but failed to update linked event booking: {e}", level='error')

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
                full_name = payment.member.get_full_name() if payment.member and payment.member.get_full_name() else payment.contact.name
                recipient_name = full_name or 'church member'
                admin_contact_number = settings.ADMIN_WHATSAPP_NUMBER

                contact_info = f"You can reach us on WhatsApp at: wa.me/{admin_contact_number.replace('+', '')}" if admin_contact_number else "Please visit the church office."

                message_text = (
                    f"Greetings {recipient_name},\n\n"
                    f"We are writing to you regarding your recent submission for a *{payment.get_payment_type_display()}* of *{payment.amount} {payment.currency}*.\n\n"
                    "There appears to be an issue with the confirmation, and we need your help to resolve it. Please contact the church accounts office at your earliest convenience so we can assist you.\n\n"
                    f"{contact_info}\n\n"
                    "Thank you for your understanding.\n"
                    "The Church Accounts Team"
                )
                if self._send_status_notification(payment, active_config, message_text):
                    notified_count += 1

            # --- New Logic: Check for and cancel related EventBooking ---
            try:
                booking = payment.event_booking
                if booking and booking.status == 'pending_payment_verification':
                    booking.status = 'cancelled'
                    booking.save(update_fields=['status'])
                    logger.info(f"Cancelled EventBooking {booking.id} for denied payment {payment.id}.")

                    # Send a specific notification for the event booking cancellation
                    if active_config and booking.contact:
                        recipient_name = booking.contact.name or 'church member'
                        event_title = booking.event.title if booking.event else "the event"
                        booking_cancellation_message = (
                            f"Hello {recipient_name},\n\n"
                            f"We're writing regarding your registration for *{event_title}*. Unfortunately, there was an issue with the payment verification, and we were unable to confirm your spot. As a result, your booking has been cancelled.\n\n"
                            "If you believe this is an error or wish to try registering again, please contact the church office.\n\n"
                            "We apologize for any inconvenience.\n\n"
                            "In His Grace,\n"
                            "The Events Team"
                        )
                        booking_message = Message.objects.create(
                            contact=booking.contact, app_config=active_config, direction='out',
                            message_type='text', content_payload={'body': booking_cancellation_message},
                            status='pending_dispatch', timestamp=timezone.now()
                        )
                        transaction.on_commit(lambda: send_whatsapp_message_task.delay(booking_message.id, active_config.id))
            except EventBooking.DoesNotExist:
                pass # Expected for non-event payments
            except Exception as e:
                logger.error(f"Error cancelling related event booking for payment {payment.id}: {e}", exc_info=True)
                self.message_user(request, f"Payment {payment.id} denied, but failed to cancel linked event booking: {e}", level='error')
        
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
    list_display = ('__str__', 'contact', 'category', 'status', 'is_anonymous', 'submitted_as_member', 'created_at')
    list_filter = ('status', 'category', 'is_anonymous', 'submitted_as_member', 'created_at')
    search_fields = ('request_text', 'contact__whatsapp_id', 'member__first_name', 'member__last_name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    actions = ['mark_as_in_progress', 'mark_as_completed']
    list_per_page = 30
    fieldsets = (
        ('Request Details', {'fields': ('id', 'status', 'category', 'request_text')}),
        ('Submitter', {'fields': ('contact', 'member', 'is_anonymous', 'submitted_as_member')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def mark_as_in_progress(self, request, queryset):
        for prayer_request in queryset:
            if prayer_request.status != 'in_prayer': # Use 'in_prayer' status
                prayer_request.status = 'in_prayer'
                prayer_request.save()                
                try:
                    active_config = MetaAppConfig.objects.get_active_config()                    
                    message = (
                        "We are lifting you up in prayer! 🙏 Your request: "
                        f"'{prayer_request.request_text[:50]}...' is now being prayed for.\n\n"
                        "\"Therefore I tell you, whatever you ask for in prayer, believe that you have received it, and it will be yours.\" - Mark 11:24\n\n"
                        "May you find comfort and strength in His presence. 🙏"
                    )
                    self._send_status_notification(request, prayer_request, active_config, message)
                except MetaAppConfig.DoesNotExist:
                    self.message_user(request, "No active Meta App Configuration found.  Notification not sent.", level='WARNING')
                except Exception as e:
                    self.message_user(request, f"An error occurred while sending the notification: {e}", level='ERROR')
            else:
                self.message_user(request, f"Prayer request {prayer_request.id} is already in progress.", level='WARNING')
    
    mark_as_in_progress.short_description = "Mark as In Progress and Notify"

    def mark_as_completed(self, request, queryset):
        for prayer_request in queryset:
            if prayer_request.status != 'answered': # use 'answered' status
                prayer_request.status = 'answered'
                prayer_request.save()                
                try:
                    active_config = MetaAppConfig.objects.get_active_config()                    
                    message = (
                        "Praise be to God! 🙏 We rejoice with you as we've completed praying for your request: "
                        f"'{prayer_request.request_text[:50]}...'\n\n"
                        "\"Rejoice always, pray continually, give thanks in all circumstances; for this is God’s will for you in Christ Jesus.\" - 1 Thessalonians 5:16-18\n\n"
                        "May God's blessings be upon you! 🙏"
                    )
                    self._send_status_notification(request, prayer_request, active_config, message)
                except MetaAppConfig.DoesNotExist:
                    self.message_user(request, "No active Meta App Configuration found. Notification not sent.", level='WARNING')
                except Exception as e:
                    self.message_user(request, f"An error occurred while sending the notification: {e}", level='ERROR')
            else:
                self.message_user(request, f"Prayer request {prayer_request.id} is already completed.", level='WARNING')

    mark_as_completed.short_description = "Mark as Answered and Notify"

    def mark_as_closed(self, request, queryset):
        for prayer_request in queryset:
            if prayer_request.status != 'closed':
                prayer_request.status = 'closed'
                prayer_request.save()
        self.message_user(request, f"{queryset.count()} prayer requests marked as closed.")

    mark_as_closed.short_description = "Mark as Closed"

    actions = ['mark_as_in_progress', 'mark_as_completed', 'mark_as_closed']


    def _send_status_notification(self, request, prayer_request: PrayerRequest, active_config: MetaAppConfig, message_text: str) -> bool:
        """Helper to create and dispatch a WhatsApp notification for a prayer request status change."""
        if not prayer_request.contact:
            self.message_user(request, f"Prayer Request {prayer_request.id} has no associated contact. Cannot send notification.", level='WARNING')
            return False

        try:
            message = Message.objects.create(contact=prayer_request.contact, app_config=active_config, direction='out', message_type='text', content_payload={'body': message_text}, status='pending_dispatch', timestamp=timezone.now())
            transaction.on_commit(
                lambda: send_whatsapp_message_task.delay(message.id, active_config.id)
            )
            return True
        except Exception as e:
            self.message_user(request, f"Failed to create and dispatch notification for prayer request {prayer_request.id}. Error: {e}", level='ERROR')
            return False

            