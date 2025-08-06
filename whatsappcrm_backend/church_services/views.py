# whatsappcrm_backend/church_services/views.py
from rest_framework import viewsets, permissions
from django.db.models import Q
from .models import Sermon
from .serializers import SermonSerializer

class SermonViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Sermons.
    Supports searching via the 'search' query parameter.
    Only published sermons are visible to non-staff users.
    """
    serializer_class = SermonSerializer
    permission_classes = [permissions.IsAuthenticated] # Or use a custom IsAdminOrReadOnly

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
