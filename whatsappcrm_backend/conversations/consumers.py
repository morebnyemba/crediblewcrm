# conversations/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import Contact, Message
from .serializers import MessageSerializer
from meta_integration.tasks import send_whatsapp_message_task
from meta_integration.models import MetaAppConfig

import logging
logger = logging.getLogger(__name__)

class ConversationConsumer(AsyncWebsocketConsumer):
    """
    Handles real-time messaging for a specific conversation.
    """
    async def connect(self):
        self.contact_id = self.scope['url_route']['kwargs']['contact_id']
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Check if user has permission to access this contact's conversation
        self.contact = await self.get_contact(self.contact_id)
        if not self.contact:
            logger.warning(f"User {self.user.id} tried to connect to non-existent contact WebSocket: {self.contact_id}")
            await self.close()
            return

        self.conversation_group_name = f'conversation_{self.contact_id}'

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"User {self.user.id} connected to conversation WebSocket for contact {self.contact_id}.")

    async def disconnect(self, close_code):
        if hasattr(self, 'conversation_group_name'):
            await self.channel_layer.group_discard(
                self.conversation_group_name,
                self.channel_name
            )
            logger.info(f"User {self.user.id} disconnected from conversation WebSocket for contact {self.contact_id}.")

    async def receive(self, text_data):
        """
        Receive a message from the WebSocket (i.e., a user sending a message from the frontend).
        """
        data = json.loads(text_data)
        message_text = data.get('message')

        if not message_text:
            return

        # Create the message in the database. The post_save signal will then broadcast it.
        await self.create_and_dispatch_message(message_text)
        logger.info(f"User {self.user.id} sent message via WebSocket to contact {self.contact_id}: '{message_text[:50]}...'")

    async def chat_message(self, event):
        """
        Handler for messages broadcast from the channel layer (from signals).
        """
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def get_contact(self, contact_id):
        return Contact.objects.filter(pk=contact_id).first()

    @database_sync_to_async
    def create_and_dispatch_message(self, message_text):
        active_config = MetaAppConfig.objects.get_active_config()
        if not active_config: return
        message = Message.objects.create(contact=self.contact, direction='out', message_type='text', content_payload={'body': message_text}, status='pending_dispatch')
        send_whatsapp_message_task.delay(message.id, active_config.id)
        return message