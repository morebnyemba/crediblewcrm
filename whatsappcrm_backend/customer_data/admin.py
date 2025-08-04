# whatsappcrm_backend/customer_data/admin.py

from django.contrib import admin
from .models import Family, MemberProfile, Payment, PaymentHistory, PrayerRequest
from django.utils.html import format_html
from django.core.files.storage import default_storage


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
        if obj.proof_of_payment_url:
            full_url = default_storage.url(obj.proof_of_payment_url)
            return format_html('<a href="{0}" target="_blank"><img src="{0}" style="max-width: 200px; max-height: 200px;" /></a>', full_url)
        return "No proof uploaded."
    display_proof_of_payment.short_description = 'Proof of Payment'


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