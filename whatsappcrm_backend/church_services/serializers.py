# whatsappcrm_backend/church_services/serializers.py
from rest_framework import serializers
from .models import Sermon, Event, Ministry, EventBooking

class SermonSerializer(serializers.ModelSerializer):
    """
    Serializer for the Sermon model.
    """
    class Meta:
        model = Sermon
        fields = [
            'id',
            'title',
            'preacher',
            'sermon_date',
            'video_link',
            'audio_link',
            'description',
            'is_published',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

class EventBookingSerializer(serializers.ModelSerializer):
    """
    Serializer for the EventBooking model.
    """
    event_title = serializers.CharField(source='event.title', read_only=True)
    contact_name = serializers.CharField(source='contact.name', read_only=True)

    class Meta:
        model = EventBooking
        fields = [
            'id',
            'booking_reference',
            'event',
            'event_title',
            'contact',
            'contact_name',
            'status',
            'booking_date',
        ]
        read_only_fields = ('id', 'booking_reference', 'booking_date', 'event_title', 'contact_name')

class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for the Event model.
    """
    class Meta:
        model = Event
        fields = [
            'id',
            'title',
            'description',
            'start_time',
            'end_time',
            'location',
            'latitude',
            'registration_fee',
            'longitude',
            'flyer',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')

class MinistrySerializer(serializers.ModelSerializer):
    """
    Serializer for the Ministry model.
    """
    class Meta:
        model = Ministry
        fields = [
            'id',
            'name',
            'description',
            'leader_name',
            'contact_info',
            'meeting_schedule',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')