# whatsappcrm_backend/conversations/views.py

from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Prefetch, Subquery, OuterRef, Count, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging # Make sure logging is imported

from .models import Contact, Message
from .serializers import (
    ContactSerializer,
    MessageSerializer,
    MessageListSerializer,
    ContactDetailSerializer,
    ContactListSerializer,
    BroadcastCreateSerializer,
)
# For dispatching Celery task
from meta_integration.tasks import send_whatsapp_message_task
# To get active MetaAppConfig for sending
from meta_integration.models import MetaAppConfig
# To personalize messages using flow template logic
from flows.services import _resolve_value

logger = logging.getLogger(__name__) # Standard way to get logger for current module

# Define permissions if not already in a central place
class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit objects.
    Others can only read. Assumes IsAuthenticated is also applied.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS: # GET, HEAD, OPTIONS
            return True
        return request.user and request.user.is_staff


class ContactViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Contacts.
    - Admins can CRUD.
    - Authenticated users can list/retrieve (permissions can be refined).
    """
    queryset = Contact.objects.all().order_by('-last_seen')
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return ContactListSerializer
        if self.action == 'retrieve':
            return ContactDetailSerializer
        return ContactSerializer

    def get_queryset(self):
        """
        Dynamically filter and annotate the queryset based on the action.
        - For 'list', add message previews and unread counts, and order by last message time.
        - For 'retrieve', prefetch related data for a detailed view.
        """
        queryset = Contact.objects.all()

        if self.action == 'list':
            # Subquery to get the text content of the latest message for each contact
            latest_message_subquery = Message.objects.filter(
                contact=OuterRef('pk')
            ).order_by('-timestamp')
            
            latest_message_preview = latest_message_subquery.values('text_content')[:1]
            latest_message_timestamp = latest_message_subquery.values('timestamp')[:1]

            queryset = queryset.annotate(
                last_message_preview=Subquery(latest_message_preview),
                # A simple unread count: incoming messages with 'received' status.
                # A more complex implementation might track read status per agent.
                unread_count=Count('messages', filter=Q(messages__direction='in', messages__status='received')),
                # Annotate the latest message timestamp to order by it
                latest_message_ts=Subquery(latest_message_timestamp)
            ).order_by(F('latest_message_ts').desc(nulls_last=True), '-last_seen')

            search_term = self.request.query_params.get('search', None)
            if search_term:
                queryset = queryset.filter(
                    Q(name__icontains=search_term) | 
                    Q(whatsapp_id__icontains=search_term)
                )

            needs_intervention_filter = self.request.query_params.get('needs_human_intervention', None)
            if needs_intervention_filter is not None:
                if needs_intervention_filter.lower() == 'true':
                    queryset = queryset.filter(needs_human_intervention=True)
                elif needs_intervention_filter.lower() == 'false':
                    queryset = queryset.filter(needs_human_intervention=False)

        elif self.action == 'retrieve':
            # For the detail view, prefetch messages in chronological order
            queryset = queryset.prefetch_related(
                Prefetch('messages', queryset=Message.objects.order_by('timestamp'))
            )
        else:
            # Fallback for other actions, use default ordering
            queryset = queryset.order_by('-last_seen')
            
        return queryset

    @action(detail=True, methods=['get'], url_path='messages', permission_classes=[permissions.IsAuthenticated])
    def list_messages_for_contact(self, request, pk=None):
        contact = get_object_or_404(Contact, pk=pk)
        # Return messages in REVERSE chronological order for pagination (most recent first)
        messages_queryset = Message.objects.filter(contact=contact).select_related('contact').order_by('-timestamp')
        
        page = self.paginate_queryset(messages_queryset)
        if page is not None:
            serializer = MessageListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = MessageListSerializer(messages_queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle-block', permission_classes=[permissions.IsAuthenticated, IsAdminOrReadOnly])
    def toggle_block_status(self, request, pk=None):
        contact = get_object_or_404(Contact, pk=pk)
        contact.is_blocked = not contact.is_blocked
        contact.save(update_fields=['is_blocked', 'last_seen']) # last_seen is auto_now
        serializer = self.get_serializer(contact)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='toggle-intervention', permission_classes=[permissions.IsAuthenticated, IsAdminOrReadOnly])
    def toggle_human_intervention(self, request, pk=None):
        """
        Toggles the 'needs_human_intervention' flag for a contact.
        """
        contact = self.get_object()
        contact.needs_human_intervention = not contact.needs_human_intervention
        if not contact.needs_human_intervention:
            # Also clear the timestamp when resolving the intervention
            contact.intervention_requested_at = None
        else:
            contact.intervention_requested_at = timezone.now()
        contact.save(update_fields=['needs_human_intervention', 'intervention_requested_at', 'last_seen'])
        
        # --- Broadcast update via WebSocket ---
        channel_layer = get_channel_layer()
        group_name = f'conversation_{contact.id}'
        
        # Use the detail serializer to get the full, updated contact representation
        serializer = ContactDetailSerializer(contact)
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {'type': 'contact_updated', 'contact': serializer.data}
        )
        logger.info(f"Broadcasted contact update for contact {contact.id} to group {group_name}.")
        
        return Response(serializer.data, status=status.HTTP_200_OK)

class MessageViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Message.objects.all().select_related('contact').order_by('-timestamp')
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly] # Adjust IsAdminOrReadOnly if non-staff should create messages

    def get_serializer_class(self):
        if self.action == 'list':
            return MessageListSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        """
        Handles the creation of an outgoing message and dispatches it for sending via Celery.
        """
        # The serializer expects 'contact' (PK), 'message_type', and 'content_payload'.
        # 'direction' and 'status' are set here for outgoing messages.
        # The request.user (agent sending the message) can also be logged if needed.
        # message_by_user = self.request.user # If you want to track which CRM user sent it

        message = serializer.save(
            direction='out',
            status='pending_dispatch', # Initial status before task picks it up
            timestamp=timezone.now() # Set send timestamp
            # created_by=message_by_user # Example if you add a 'created_by' FK to User
        )
        
        logger.info(
            f"Message record {message.id} created for contact {message.contact.whatsapp_id} "
            f"by user {self.request.user}. Type: {message.message_type}. Status: {message.status}."
        )

        try:
            # Fetch the active MetaAppConfig to get credentials for sending
            # This assumes MetaAppConfig has a manager method get_active_config()
            active_config = MetaAppConfig.objects.get_active_config()
            
            if active_config:
                logger.info(f"Dispatching Celery task send_whatsapp_message_task for Message ID: {message.id} using Config ID: {active_config.id}")
                send_whatsapp_message_task.delay(message.id, active_config.id)
                # The message status will be updated by the Celery task (e.g., to 'sent' or 'failed')
            else:
                logger.error(f"No active MetaAppConfig found. Message {message.id} for contact {message.contact.whatsapp_id} cannot be dispatched.")
                message.status = 'failed'
                message.error_details = {'error': 'No active MetaAppConfig was found for sending this message.'}
                message.status_timestamp = timezone.now()
                message.save(update_fields=['status', 'error_details', 'status_timestamp'])
        
        except MetaAppConfig.DoesNotExist:
            logger.critical(f"CRITICAL: No MetaAppConfig marked as active. Message {message.id} cannot be dispatched.")
            message.status = 'failed'; message.error_details = {'error': 'No active MetaAppConfig available.'}
            message.status_timestamp = timezone.now()
            message.save(update_fields=['status', 'error_details', 'status_timestamp'])
        except MetaAppConfig.MultipleObjectsReturned:
            logger.critical(f"CRITICAL: Multiple active MetaAppConfigs found. Message {message.id} cannot be dispatched reliably.")
            message.status = 'failed'; message.error_details = {'error': 'Multiple active MetaAppConfigs found.'}
            message.status_timestamp = timezone.now()
            message.save(update_fields=['status', 'error_details', 'status_timestamp'])
        except Exception as e:
            logger.error(f"Error dispatching Celery task for Message ID {message.id}: {e}", exc_info=True)
            message.status = 'failed'
            message.error_details = {'error': f'Failed to dispatch send task: {str(e)}'}
            message.status_timestamp = timezone.now()
            message.save(update_fields=['status', 'error_details', 'status_timestamp'])


    def get_queryset(self):
        queryset = super().get_queryset()
        contact_id = self.request.query_params.get('contact_id')
        if contact_id:
            try:
                queryset = queryset.filter(contact_id=int(contact_id))
            except ValueError:
                logger.warning(f"Invalid contact_id query parameter: {contact_id}")
                return Message.objects.none() # Return empty for invalid ID
        
        search_term = self.request.query_params.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(text_content__icontains=search_term) |
                Q(contact__name__icontains=search_term) |
                Q(contact__whatsapp_id__icontains=search_term)
            )
        return queryset


class BroadcastViewSet(viewsets.ViewSet):
    """
    API endpoint for sending business-initiated template messages (broadcasts).
    """
    permission_classes = [permissions.IsAdminUser] # Only admins can broadcast

    @action(detail=False, methods=['post'], url_path='send-template')
    def send_template_message(self, request):
        """
        Receives a list of contact IDs and a template to send.
        Creates personalized messages and queues them for sending.
        """
        serializer = BroadcastCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        contact_ids = validated_data['contact_ids']
        template_name = validated_data['template_name']
        language_code = validated_data['language_code']
        components_template = validated_data.get('components')

        try:
            active_config = MetaAppConfig.objects.get_active_config()
            if not active_config:
                raise Exception("No active Meta App Configuration found.")
        except Exception as e:
            logger.error(f"Broadcast failed: Could not get active Meta config. Error: {e}")
            return Response({"error": "Server configuration error: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Fetch all contacts and their profiles in a single query to be efficient
        contacts_to_message = Contact.objects.filter(id__in=contact_ids).select_related('member_profile')
        
        dispatched_count = 0
        for contact in contacts_to_message:
            # Construct the payload for this specific contact
            components = _resolve_value(components_template, {}, contact) if components_template else None

            content_payload = {
                "name": template_name,
                "language": {"code": language_code}
            }
            if components:
                content_payload["components"] = components

            # Create the Message object
            message = Message.objects.create(
                contact=contact, meta_app_config=active_config, direction='out',
                message_type='template', content_payload=content_payload,
                status='pending_dispatch', timestamp=timezone.now()
            )

            # Dispatch the Celery task for sending
            send_whatsapp_message_task.delay(message.id, active_config.id)
            dispatched_count += 1
            logger.info(f"Dispatched template broadcast message {message.id} to contact {contact.id} ({contact.whatsapp_id})")

        return Response({
            "message": f"Broadcast dispatch initiated for {dispatched_count} of {len(contact_ids)} requested contacts.",
        }, status=status.HTTP_202_ACCEPTED)
        return queryset