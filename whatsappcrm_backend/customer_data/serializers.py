# whatsappcrm_backend/customer_data/serializers.py
from rest_framework import serializers
from .models import MemberProfile, Family

class FamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = '__all__'

class MemberProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberProfile
        fields = [
            'contact',
            'first_name',
            'last_name',
            'email',
            'secondary_phone_number',
            'date_of_birth',
            'gender',
            'marital_status',
            'family',
            'date_joined',
            'baptism_date',
            'address_line_1',
            'address_line_2',
            'city',
            'state_province',
            'postal_code',
            'country',
            'membership_status',
            'acquisition_source',
            'tags',
            'notes',
            'preferences',
            'custom_attributes',
            'created_at',
            'updated_at',
            'last_updated_from_conversation'
        ]
        read_only_fields = ('contact', 'created_at', 'updated_at', 'last_updated_from_conversation')

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list.")
        if not all(isinstance(tag, str) for tag in value):
            raise serializers.ValidationError("All tags must be strings.")
        return value

    def validate_preferences(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Preferences must be a JSON object (dictionary).")
        return value

    def validate_custom_attributes(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Custom attributes must be a JSON object (dictionary).")
        return value