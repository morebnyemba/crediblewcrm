# whatsappcrm_backend/customer_data/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from django.http import Http404


from .models import MemberProfile, Family, Payment, PendingVerificationPayment, PaymentHistory, PrayerRequest
from paynow_integration.tasks import process_paynow_ipn_task
from .serializers import (
    MemberProfileSerializer, FamilySerializer, PaymentSerializer, PaymentHistorySerializer, PrayerRequestSerializer
)
from conversations.models import Contact # To ensure contact exists for profile creation/retrieval

import logging
logger = logging.getLogger(__name__)

class IsAdminOrUpdateOnly(permissions.BasePermission): # Example, adjust as needed
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class MemberProfileViewSet(viewsets.ModelViewSet):
    queryset = MemberProfile.objects.select_related('contact').all()
    serializer_class = MemberProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrUpdateOnly]
    
    # MemberProfile's PK is contact_id
    # DRF ModelViewSet will use 'pk' from URL by default.
    # Since MemberProfile.pk IS contact_id, this works.
    # The URL will be /profiles/{pk}/ where pk is the contact_id.
    lookup_field = 'pk' # Explicitly state we are looking up by the primary key (contact_id)

    def get_object(self):
        """
        Override get_object to use the PK from the URL, which is the contact_id.
        If the profile doesn't exist for a GET/PUT/PATCH, create it on-the-fly.
        """
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get(self.lookup_url_kwarg or 'pk') # Default lookup is 'pk'

        try:
            obj = queryset.get(pk=pk) # pk here is contact_id
            self.check_object_permissions(self.request, obj)
            return obj
        except MemberProfile.DoesNotExist:
            # If profile doesn't exist but contact does, create profile for GET/PUT/PATCH.
            if self.request.method in ['GET', 'PUT', 'PATCH']:
                contact = get_object_or_404(Contact, pk=pk) # Check if contact exists
                obj, created = MemberProfile.objects.get_or_create(contact=contact)
                if created:
                    logger.info(f"MemberProfile created on-the-fly for Contact ID: {pk} during {self.request.method} action.")
                self.check_object_permissions(self.request, obj)
                return obj
            raise Http404("MemberProfile not found and action is not retrieve/update.")

    def perform_update(self, serializer):
        # Set last_updated_from_conversation when an agent/API updates the profile
        serializer.save(last_updated_from_conversation=timezone.now())
        logger.info(f"MemberProfile for Contact ID {serializer.instance.contact_id} updated by {self.request.user}.")

    # perform_create is usually not needed for a OneToOneProfile that's auto-created
    # or created on first update/get. If you want an explicit POST to /profiles/
    # to create one (expecting contact_id in payload), that's also possible.
    # The get_or_create in get_object handles on-demand creation for GET/PUT/PATCH.

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def paynow_ipn_webhook(request):
    """
    Handles the Instant Payment Notification from Paynow.
    It dispatches the processing to a Celery task to avoid blocking Paynow.
    """
    ipn_data = request.data
    logger.info(f"Paynow IPN received: {ipn_data}")
    process_paynow_ipn_task.delay(ipn_data)
    return Response(status=status.HTTP_200_OK)


class FamilyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Family units.
    """
    queryset = Family.objects.prefetch_related('members').all()
    serializer_class = FamilySerializer
    permission_classes = [permissions.IsAuthenticated] # Adjust permissions as needed


class PaymentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Payments.
    Provides full CRUD for payments. The model's save method handles history creation.
    """
    queryset = Payment.objects.select_related('member', 'contact').prefetch_related('history').all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated] # Adjust as needed


class PaymentHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Payment History.
    This is a read-only view as history is created automatically.
    Supports filtering by payment ID, e.g., /api/payment-history/?payment_id=<uuid>
    """
    queryset = PaymentHistory.objects.select_related('payment').all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['payment'] # Allows filtering like ?payment=<payment_id>


class PrayerRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Prayer Requests.
    """
    queryset = PrayerRequest.objects.select_related('member', 'contact').all()
    serializer_class = PrayerRequestSerializer
    permission_classes = [permissions.IsAuthenticated] # Adjust as needed