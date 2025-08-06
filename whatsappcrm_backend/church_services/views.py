# whatsappcrm_backend/church_services/views.py
from rest_framework import viewsets, permissions
from django.db.models import Q
from .models import Sermon, Event, Ministry
from .serializers import SermonSerializer, EventSerializer, MinistrySerializer

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    Others can only read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class SermonViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Sermons.
    Supports searching via the 'search' query parameter.
    Only published sermons are visible to non-staff users.
    """
    serializer_class = SermonSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        """
        Admins see all sermons. Other authenticated users see only published sermons.
        """
        user = self.request.user
        if user and user.is_staff:
            queryset = Sermon.objects.all()
        else:
            queryset = Sermon.objects.filter(is_published=True)

        search_term = self.request.query_params.get('search', None)
        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(preacher__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        return queryset.order_by('-sermon_date')

class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Events.
    Only active events are visible to non-staff users.
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_staff:
            queryset = Event.objects.all()
        else:
            queryset = Event.objects.filter(is_active=True)
        
        return queryset.order_by('start_time')

class MinistryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Ministries.
    Only active ministries are visible to non-staff users.
    """
    serializer_class = MinistrySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user and user.is_staff:
            queryset = Ministry.objects.all()
        else:
            queryset = Ministry.objects.filter(is_active=True)
        
        return queryset.order_by('name')
