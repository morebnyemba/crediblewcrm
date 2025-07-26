# whatsappcrm_backend/customer_data/admin.py

from django.contrib import admin
from .models import MemberProfile, Family

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('name', 'head_of_household', 'member_count', 'created_at')
    search_fields = ('name', 'head_of_household__name', 'head_of_household__whatsapp_id')
    list_select_related = ('head_of_household',)

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = "Members"

@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = (
        'contact_whatsapp_id', 
        'get_profile_full_name', # Use the method for display
        'membership_status',
        'family',
        'contact_first_interaction_at',
        'last_updated_from_conversation',
        'updated_at',
    )
    search_fields = (
        'contact__whatsapp_id', 
        'contact__name', 
        'first_name', 
        'last_name', 
        'email',
        'family__name',
        'preferences', 
        'custom_attributes',
        'tags'
    )
    list_filter = (
        'membership_status',
        'family',
        'contact__first_seen', 
        'last_updated_from_conversation', 
        'updated_at',
        'country',
        'gender',
        'marital_status',
    )
    readonly_fields = (
        'contact', 
        'created_at', 
        'updated_at', 
        'contact_first_interaction_at'
    )

    fieldsets = (
        (None, {'fields': ('contact',)}),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'secondary_phone_number', 'date_of_birth', 'gender', 'marital_status')
        }),
        ('Church & Family Information', {
            'fields': ('family', 'membership_status', 'date_joined', 'baptism_date')
        }),
        ('Location Information', {
            'fields': ('address_line_1', 'address_line_2', 'city', 'state_province', 'postal_code', 'country')
        }),
        ('Engagement Data', {
            'fields': ('acquisition_source', 'tags', 'notes')
        }),
        ('Collected Flow Data (JSON)', {
            'fields': ('preferences', 'custom_attributes'),
            'classes': ('collapse',), # Keep JSON fields collapsible
        }),
        ('Timestamps', {
            'fields': ( 'contact_first_interaction_at', 'created_at', 'updated_at', 'last_updated_from_conversation'),
            'classes': ('collapse',)
        }),
    )
    
    list_select_related = ('contact', 'family') # Optimization

    def contact_whatsapp_id(self, obj):
        return obj.contact.whatsapp_id
    contact_whatsapp_id.short_description = "WhatsApp ID"
    contact_whatsapp_id.admin_order_field = 'contact__whatsapp_id'

    def get_profile_full_name(self, obj):
        name = obj.get_full_name()
        return name if name else (obj.contact.name or '-') # Fallback to contact name
    get_profile_full_name.short_description = "Profile Name"
    get_profile_full_name.admin_order_field = 'last_name' # Example: sort by last_name

    def contact_first_interaction_at(self, obj):
        if obj.contact:
            return obj.contact.first_seen
        return None
    contact_first_interaction_at.short_description = "Conversation Initiated"
    contact_first_interaction_at.admin_order_field = 'contact__first_seen'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('contact')
