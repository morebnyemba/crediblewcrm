# whatsappcrm_backend/church_services/serializers.py
from rest_framework import serializers
from .models import Sermon, Event, Ministry

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