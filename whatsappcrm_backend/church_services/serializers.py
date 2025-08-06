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