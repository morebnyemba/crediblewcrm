# whatsappcrm_backend/customer_data/serializers.py
from rest_framework import serializers
from .models import Family, MemberProfile, Payment, PaymentHistory, PrayerRequest
from conversations.models import Contact

# To provide more context on related fields, we can use a simple serializer
class SimpleContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'whatsapp_id', 'name']

class MemberProfileSerializer(serializers.ModelSerializer):
    # The primary key of MemberProfile is 'contact', which is a OneToOneField.
    # DRF handles this, 'pk' in the URL will map to 'contact_id'.
    contact = SimpleContactSerializer(read_only=True)
    
    # To make choices human-readable in API responses
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    marital_status_display = serializers.CharField(source='get_marital_status_display', read_only=True)
    membership_status_display = serializers.CharField(source='get_membership_status_display', read_only=True)
    
    class Meta:
        model = MemberProfile
        # The 'contact' field is the PK, so it's implicitly read-only here
        # but can be written to on creation if not using the on-the-fly creation in the view.
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'last_updated_from_conversation')

class FamilySerializer(serializers.ModelSerializer):
    # Use MemberProfileSerializer for a nested representation of members
    members = MemberProfileSerializer(many=True, read_only=True)
    # For writing, we might accept a list of contact_ids
    member_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=MemberProfile.objects.all(), source='members', write_only=True, required=False
    )
    head_of_household_details = MemberProfileSerializer(source='head_of_household.member_profile', read_only=True)

    class Meta:
        model = Family
        fields = [
            'id', 'name', 'head_of_household', 'head_of_household_details', 
            'members', 'member_ids', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')

class PaymentHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PaymentHistory
        fields = ['id', 'payment', 'status', 'status_display', 'timestamp', 'notes']
        read_only_fields = ('id', 'payment', 'status', 'status_display', 'timestamp') # Notes can be added by admin

class PaymentSerializer(serializers.ModelSerializer):
    # Display human-readable choice values
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)

    # Provide some context on the member/contact
    member_details = MemberProfileSerializer(source='member', read_only=True)
    contact_details = SimpleContactSerializer(source='contact', read_only=True)

    # The history can be nested and read-only
    history = PaymentHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'member', 'member_details', 'contact', 'contact_details', 'amount', 'currency',
            'payment_type', 'payment_type_display', 'payment_method', 'payment_method_display',
            'status', 'status_display', 'transaction_reference', 'external_data', 'notes',
            'proof_of_payment', 'history', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'history')

    def create(self, validated_data):
        # The model's save() method handles history creation, so we just call super.
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # The model's save() method handles history creation on status change.
        return super().update(instance, validated_data)

class PrayerRequestSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    member_details = MemberProfileSerializer(source='member', read_only=True)
    contact_details = SimpleContactSerializer(source='contact', read_only=True)
    
    # To hide submitter info if anonymous
    submitter_name = serializers.SerializerMethodField()

    class Meta:
        model = PrayerRequest
        fields = [
            'id', 'member', 'member_details', 'contact', 'contact_details', 'submitter_name', 'submitted_as_member',
            'request_text', 'category', 'category_display', 'is_anonymous',
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'submitter_name')

    def get_submitter_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        if obj.member and obj.member.get_full_name():
            return obj.member.get_full_name()
        if obj.contact:
            return obj.contact.name or obj.contact.whatsapp_id
        return "Unknown"