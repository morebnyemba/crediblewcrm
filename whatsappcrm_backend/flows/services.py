# whatsappcrm_backend/flows/services.py
from django.db import models
import logging
import uuid
import json
import re
from typing import List, Dict, Any, Optional

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.apps import apps
from django.forms.models import model_to_dict
from django.urls import reverse
from jinja2 import Environment, select_autoescape, Undefined
from django.core.exceptions import ValidationError as DjangoValidationError # noqa
from pydantic import ValidationError
from django.conf import settings
from django.http import HttpRequest
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from conversations.models import Contact, Message
from .models import Flow, FlowStep, FlowTransition, ContactFlowState
from customer_data.models import MemberProfile, Payment
from customer_data.utils import record_payment, record_prayer_request, record_event_booking
from notifications.services import queue_notifications_to_users
from .tasks import resolve_human_intervention_after_timeout
from paynow_integration.services import PaynowService
from paynow_integration.tasks import poll_paynow_transaction_status
try:
    from media_manager.models import MediaAsset # For asset_pk lookup
    MEDIA_ASSET_ENABLED = True
except ImportError:
    MEDIA_ASSET_ENABLED = False

from .schemas import (
    MediaMessageContent, StepConfigSendMessage, StepConfigQuestion, StepConfigAction, StepConfigHumanHandover,
    StepConfigEndFlow, StepConfigSwitchFlow, FallbackConfig
)

logger = logging.getLogger(__name__)

# Log MediaAsset status at module load time
if not MEDIA_ASSET_ENABLED:
    logger.warning("MediaAsset model not found or could not be imported. MediaAsset functionality (e.g., 'asset_pk') will be disabled in flows.")

# --- Jinja2 Environment Setup ---
# A custom undefined type for Jinja that doesn't raise an error for missing variables,
# but returns an empty string instead.
class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return '' # Return empty string for undefined variables

def strftime_filter(value, format_string='%b %d, %Y'):
    """
    Jinja2 filter to format a date/datetime object or string using strftime.
    """
    if not value:
        return ""
    
    dt_obj = None
    if isinstance(value, str):
        dt_obj = parse_datetime(value)
        if not dt_obj:
            # Try parsing as just a date if datetime fails
            try:
                dt_obj = datetime.strptime(value, '%Y-%m-%d')
            except (ValueError, TypeError):
                return value # Return original string if parsing fails
    elif isinstance(value, (datetime, date)):
        dt_obj = value
    
    return dt_obj.strftime(format_string) if dt_obj else value

def truncatewords_filter(value, length=25, end_text='...'):
    """
    Jinja2 filter to truncate a string after a certain number of words.
    """
    if not isinstance(value, str):
        return value
    words = value.split()
    if len(words) <= length:
        return value
    return ' '.join(words[:length]) + end_text

jinja_env = Environment(
    loader=None, # We're loading templates from strings, not files
    autoescape=select_autoescape(['html', 'xml'], disabled_extensions=('txt',), default_for_string=False),
    undefined=SilentUndefined,
    enable_async=False
)
jinja_env.filters['strftime'] = strftime_filter # Add the custom filter
jinja_env.filters['truncatewords'] = truncatewords_filter # Add the new filter
jinja_env.globals['now'] = timezone.now # Make 'now' globally available for date comparisons


def _initiate_paynow_payment(contact: Contact, amount_str: str, payment_type: str, payment_method: str, phone_number: str, email: str, currency: str, notes: str) -> dict:
    """
    Handles the logic for initiating a Paynow payment.
    Creates a Payment record, calls Paynow service, and returns context updates.
    """
    # 1. Validate amount
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError("Amount must be positive.")
    except (InvalidOperation, ValueError) as e:
        logger.error(f"Contact {contact.id}: Invalid amount '{amount_str}' for Paynow initiation. Error: {e}")
        return {
            'paynow_initiation_success': False,
            'paynow_initiation_error': f"Invalid amount provided: {amount_str}"
        }

    # 2. Create a pending Payment record
    payment = Payment.objects.create(
        contact=contact,
        member=getattr(contact, 'member_profile', None),
        amount=amount,
        currency=currency or "USD",
        payment_type=payment_type or "other",
        payment_method=payment_method,
        status='pending',
        notes=notes or "Online giving via WhatsApp flow (Paynow).",
    )
    logger.info(f"Contact {contact.id}: Created pending Payment record {payment.id} for Paynow initiation.")

    # 3. Call Paynow Service
    try:
        # The IPN URL is constructed here by reversing the named URL from the customer_data app.
        # This is more robust than having the service guess the URL, which can cause NoReverseMatch errors.
        ipn_callback_url = reverse('customer_data_api:paynow-ipn-webhook')
        paynow_service = PaynowService(ipn_callback_url=ipn_callback_url)
    except Exception as e:
        logger.error(f"Failed to initialize PaynowService for contact {contact.id}. Error: {e}", exc_info=True)
        # Update payment status to failed to reflect the initialization failure
        payment.status = 'failed'
        payment.notes += f"\nPaynow service failed to initialize: {e}"
        payment.save(update_fields=['status', 'notes', 'updated_at'])
        # Return a user-friendly error to the flow context
        return {
            'paynow_initiation_success': False,
            'paynow_initiation_error': 'Paynow service could not be configured.',
            'last_payment_id': str(payment.id)
        }


    paynow_method_map = {'ecocash': 'ecocash'}
    paynow_method_type = paynow_method_map.get(str(payment_method).lower())

    if not paynow_method_type:
        payment.status = 'failed'
        payment.notes += f"\nUnsupported payment method for Paynow: {payment_method}"
        payment.save(update_fields=['status', 'notes', 'updated_at'])
        return {
            'paynow_initiation_success': False,
            'paynow_initiation_error': f"Payment method '{payment_method}' is not supported for automated payments."
        }

    # Use a default email if none is provided, as Paynow requires it.
    final_email = email or f"{contact.whatsapp_id}@crediblewcrm.co.zw"

    paynow_response = paynow_service.initiate_express_checkout_payment(
        amount=amount,
        reference=str(payment.id), # Use our internal Payment UUID as the reference
        phone_number=phone_number,
        email=final_email,
        paynow_method_type=paynow_method_type,
        description=f"{str(payment_type).title()} from {contact.name or contact.whatsapp_id}"
    )

    # 5. Handle response
    if paynow_response.get('success'):
        payment.transaction_reference = paynow_response.get('paynow_reference')
        # Be explicit about what is saved to the JSONField to prevent serialization errors.
        # Only store known, safe, and useful data from the response.
        payment.external_data = {
            'poll_url': paynow_response.get('poll_url'),
            'initiation_response': {
                'success': paynow_response.get('success'),
                'status': paynow_response.get('status'),
                'paynow_reference': paynow_response.get('paynow_reference'),
                'message': paynow_response.get('message'),
            }
        }
        payment.save(update_fields=['transaction_reference', 'external_data', 'updated_at'])
        
        # Use transaction.on_commit to ensure the task is dispatched only after the
        # payment record has been successfully saved to the database, preventing race conditions.
        transaction.on_commit(lambda: poll_paynow_transaction_status.delay(payment_id=str(payment.id)))
        logger.info(f"Contact {contact.id}: Paynow initiation successful for Payment {payment.id}. Polling task scheduled.")
        return {'paynow_initiation_success': True, 'last_payment_id': str(payment.id)}
    else:
        error_message = paynow_response.get('message', 'Unknown error from Paynow.')
        payment.status = 'failed'
        payment.notes += f"\nPaynow initiation failed: {error_message}"
        payment.save(update_fields=['status', 'notes', 'updated_at'])
        logger.error(f"Contact {contact.id}: Paynow initiation failed for Payment {payment.id}. Reason: {error_message}")
        return {'paynow_initiation_success': False, 'paynow_initiation_error': error_message, 'last_payment_id': str(payment.id)}

def _get_value_from_context_or_contact(variable_path: str, flow_context: dict, contact: Contact) -> Any:
	"""
	Resolves a variable path (e.g., 'contact.name', 'user_email') to its value
	by rendering it as a Jinja2 template. This is safer and more consistent.
	"""
	if not isinstance(variable_path, str):
		return variable_path

	# The variable path is treated as a Jinja2 expression.
	# e.g., "contact.name", "payment_history_list.0.amount"
	template_string = f"{{{{ {variable_path} }}}}"
	resolved_value = _resolve_value(template_string, flow_context, contact)

	# Jinja returns an empty string for undefined variables. If the original path
	# was just the variable name, we can interpret an empty string result as None.
	if resolved_value == '' and template_string == f"{{{{ {resolved_value} }}}}":
		return None

	return resolved_value

def _resolve_value(template_value: Any, flow_context: dict, contact: Contact) -> Any:
    """
    Resolves a template value using Jinja2, which can be a string, dict, or list.
    Provides 'contact', 'member_profile', and the flow_context to the template.
    """
    if isinstance(template_value, str):
        # Use Jinja2 for powerful string templating, supporting loops, conditionals, and filters.
        try:
            template = jinja_env.from_string(template_value)
            # The context for Jinja includes the contact, their profile, and the flow context flattened.
            render_context = {
                **flow_context,
                'contact': contact,
                'member_profile': getattr(contact, 'member_profile', None)
            }
            return template.render(render_context)
        except Exception as e:
            logger.error(f"Jinja2 template rendering failed for contact {contact.id}: {e}. Template: '{template_value}'", exc_info=False)
            return template_value # Return original on error
    elif isinstance(template_value, dict):
        # Recursively resolve values in a dictionary
        return {k: _resolve_value(v, flow_context, contact) for k, v in template_value.items()}
    elif isinstance(template_value, list):
        # Recursively resolve values in a list
        return [_resolve_value(item, flow_context, contact) for item in template_value]
    
    # For non-string, non-dict, non-list types, return as is
    return template_value

def _resolve_template_components(components_config: list, flow_context: dict, contact: Contact) -> list:
    if not components_config or not isinstance(components_config, list): return []
    try:
        resolved_components_list = json.loads(json.dumps(components_config)) # Deep copy
        for component in resolved_components_list:
            if isinstance(component.get('parameters'), list):
                for param in component['parameters']:
                    # Resolve text for any parameter type that might contain it
                    if 'text' in param and isinstance(param['text'], str):
                        param['text'] = _resolve_value(param['text'], flow_context, contact)
                    
                    # Specific handling for media link in header/body components using image/video/document type parameters
                    param_type = param.get('type')
                    if param_type in ['image', 'video', 'document'] and isinstance(param.get(param_type), dict):
                        media_obj = param[param_type]
                        if 'link' in media_obj and isinstance(media_obj['link'], str):
                             media_obj['link'] = _resolve_value(media_obj['link'], flow_context, contact)
                    
                    # Handle payload for button parameters
                    if component.get('type') == 'button' and param.get('type') == 'payload' and 'payload' in param and isinstance(param['payload'], str):
                         param['payload'] = _resolve_value(param['payload'], flow_context, contact)

                    # Handle currency and date_time fallback_values
                    if param_type == 'currency' and isinstance(param.get('currency'), dict) and 'fallback_value' in param['currency']:
                        param['currency']['fallback_value'] = _resolve_value(param['currency']['fallback_value'], flow_context, contact)
                    if param_type == 'date_time' and isinstance(param.get('date_time'), dict) and 'fallback_value' in param['date_time']:
                        param['date_time']['fallback_value'] = _resolve_value(param['date_time']['fallback_value'], flow_context, contact)

        return resolved_components_list
    except Exception as e:
        logger.error(f"Error resolving template components: {e}. Config: {components_config}", exc_info=True)
        return components_config

def _clear_contact_flow_state(contact: Contact, error: bool = False):
    deleted_count, _ = ContactFlowState.objects.filter(contact=contact).delete()
    if deleted_count > 0:        
        logger.info(f"Contact {contact.id}: Cleared flow state ({contact.whatsapp_id})." + (" Due to an error." if error else ""))

def _execute_step_actions(step: FlowStep, contact: Contact, flow_context: dict, request: Optional[HttpRequest] = None, is_re_execution: bool = False) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    actions_to_perform = []
    raw_step_config = step.config or {} 
    current_step_context = flow_context.copy() 

    logger.debug(
        f"Contact {contact.id}: Executing actions for step '{step.name}' (ID: {step.id}, Type: {step.step_type}). "
        f"Raw Config: {raw_step_config}"
    )

    if step.step_type == 'send_message':
        try:
            # --- FIX: Pre-resolve message_type if it's a template before validation ---
            config_to_validate = raw_step_config.copy()
            potential_message_type = config_to_validate.get('message_type', '')
            
            # Check if the message_type field contains Jinja templating
            if isinstance(potential_message_type, str) and '{%' in potential_message_type:
                resolved_type = _resolve_value(potential_message_type, current_step_context, contact)
                config_to_validate['message_type'] = resolved_type
                logger.debug(f"Contact {contact.id}: Dynamically resolved message_type from '{potential_message_type}' to '{resolved_type}'.")

            send_message_config = StepConfigSendMessage.model_validate(config_to_validate)
            actual_message_type = send_message_config.message_type

            final_api_data_structure = {}
            
            if actual_message_type == "text" and send_message_config.text:
                text_content = send_message_config.text
                resolved_body = _resolve_value(text_content.body, current_step_context, contact)
                final_api_data_structure = {'body': resolved_body, 'preview_url': text_content.preview_url}

            elif actual_message_type in ['image', 'document', 'audio', 'video', 'sticker'] and getattr(send_message_config, actual_message_type):
                media_conf: MediaMessageContent = getattr(send_message_config, actual_message_type)
                media_data_to_send = {}
                
                valid_source_found = False
                if MEDIA_ASSET_ENABLED and media_conf.asset_pk:
                    try:
                        asset = MediaAsset.objects.get(pk=media_conf.asset_pk)
                        if asset.status == 'synced' and asset.whatsapp_media_id and not asset.is_whatsapp_id_potentially_expired():
                            media_data_to_send['id'] = asset.whatsapp_media_id
                            valid_source_found = True
                            logger.info(f"Contact {contact.id}: Using MediaAsset {asset.pk} ('{asset.name}') with WA ID: {asset.whatsapp_media_id} for step {step.id}.")
                        else: 
                            logger.warning(f"Contact {contact.id}: MediaAsset {asset.pk} ('{asset.name}') not usable for step {step.id} (Status: {asset.status}, Expired: {asset.is_whatsapp_id_potentially_expired()}). Trying direct id/link from config.")
                    except MediaAsset.DoesNotExist:
                        logger.error(f"Contact {contact.id}: MediaAsset pk={media_conf.asset_pk} not found for step {step.id}. Trying direct id/link from config.")
                
                if not valid_source_found: # Try direct id or link if asset_pk didn't work or wasn't provided
                    if media_conf.id:
                        media_data_to_send['id'] = _resolve_value(media_conf.id, current_step_context, contact)
                        valid_source_found = True
                    elif media_conf.link:
                        resolved_link = _resolve_value(media_conf.link, current_step_context, contact)
                        # --- FIX: Ensure the link is an absolute URL ---
                        if resolved_link.startswith('/') and request:
                            media_data_to_send['link'] = request.build_absolute_uri(resolved_link)
                            logger.debug(f"Contact {contact.id}: Converted relative media link '{resolved_link}' to absolute URL '{media_data_to_send['link']}'.")
                        else:
                            media_data_to_send['link'] = resolved_link
                        valid_source_found = True
                
                if not valid_source_found:
                    logger.error(f"Contact {contact.id}: No valid media source (asset_pk, id, or link) for {actual_message_type} in step '{step.name}' (ID: {step.id}).")
                else:
                    if media_conf.caption:
                        media_data_to_send['caption'] = _resolve_value(media_conf.caption, current_step_context, contact)
                    if actual_message_type == 'document' and media_conf.filename:
                        media_data_to_send['filename'] = _resolve_value(media_conf.filename, current_step_context, contact)
                    final_api_data_structure = media_data_to_send
            
            elif actual_message_type == "interactive" and send_message_config.interactive:
                interactive_payload_validated = send_message_config.interactive # Already validated by StepConfigSendMessage
                interactive_payload_dict = interactive_payload_validated.model_dump(exclude_none=True, by_alias=True)
                
                # Resolve templates directly within the dictionary structure
                final_api_data_structure = _resolve_value(interactive_payload_dict, current_step_context, contact)

            elif actual_message_type == "template" and send_message_config.template:
                template_payload_validated = send_message_config.template
                template_payload_dict = template_payload_validated.model_dump(exclude_none=True, by_alias=True)
                if 'components' in template_payload_dict and template_payload_dict['components']:
                    template_payload_dict['components'] = _resolve_template_components(
                        template_payload_dict['components'], current_step_context, contact
                    )
                final_api_data_structure = template_payload_dict
            
            elif actual_message_type == "contacts" and send_message_config.contacts:
                contacts_list_of_objects = send_message_config.contacts
                contacts_list_of_dicts = [c.model_dump(exclude_none=True, by_alias=True) for c in contacts_list_of_objects]
                resolved_contacts = _resolve_value(contacts_list_of_dicts, current_step_context, contact)
                final_api_data_structure = {"contacts": resolved_contacts}

            elif actual_message_type == "location" and send_message_config.location:
                location_obj = send_message_config.location
                location_dict = location_obj.model_dump(exclude_none=True, by_alias=True)
                # --- FIX: The send_whatsapp_message utility wraps the data in a key matching the message_type.
                # We should provide only the inner dictionary of location details, not a dict containing a 'location' key.
                # The utility will create the final payload: {"type": "location", "location": {...}}
                final_api_data_structure = _resolve_value(location_dict, current_step_context, contact)

            if final_api_data_structure:
                actions_to_perform.append({
                    'type': 'send_whatsapp_message',
                    'recipient_wa_id': contact.whatsapp_id,
                    'message_type': actual_message_type,
                    'data': final_api_data_structure
                })
            elif actual_message_type: # If type was specified but no payload generated
                 logger.warning(f"Contact {contact.id}: No data payload generated for message_type '{actual_message_type}' in step '{step.name}' (ID: {step.id}). Pydantic Config: {send_message_config.model_dump_json(indent=2) if send_message_config else None}")

        except ValidationError as e:
            logger.error(f"Contact {contact.id}: Pydantic validation error for 'send_message' step '{step.name}' (ID: {step.id}) config: {e.errors()}. Raw config: {raw_step_config}", exc_info=False)
        except Exception as e:
            logger.error(f"Contact {contact.id}: Unexpected error processing 'send_message' step '{step.name}' (ID: {step.id}): {e}", exc_info=True)

    elif step.step_type == 'question':
        try:
            question_config = StepConfigQuestion.model_validate(raw_step_config)
            if question_config.message_config and not is_re_execution: # Only send initial prompt if not a re-execution for fallback
                try:
                    temp_msg_pydantic_config = StepConfigSendMessage.model_validate(question_config.message_config)
                    dummy_send_step = FlowStep(name=f"{step.name}_prompt", step_type="send_message", config=temp_msg_pydantic_config.model_dump(exclude_none=True))
                    send_actions, _ = _execute_step_actions(dummy_send_step, contact, current_step_context, request=request) # Pass request
                    actions_to_perform.extend(send_actions)
                except ValidationError as ve:
                    logger.error(f"Contact {contact.id}: Pydantic validation error for 'message_config' within 'question' step '{step.name}' (ID: {step.id}): {ve.errors()}", exc_info=False)
            
            if question_config.reply_config: # This part is always active for a question step
                current_step_context['_question_awaiting_reply_for'] = {
                    'variable_name': question_config.reply_config.save_to_variable,
                    'expected_type': question_config.reply_config.expected_type,
                    'validation_regex': question_config.reply_config.validation_regex,
                    'original_question_step_id': step.id 
                }
                logger.debug(f"Step '{step.name}' is a question, awaiting reply for: {question_config.reply_config.save_to_variable}")
        except ValidationError as e:
            logger.error(f"Contact {contact.id}: Pydantic validation for 'question' step '{step.name}' (ID: {step.id}) failed: {e.errors()}", exc_info=False)

    elif step.step_type == 'action':
        try:
            action_step_config = StepConfigAction.model_validate(raw_step_config)
            for action_item_conf in action_step_config.actions_to_run:
                action_type = action_item_conf.action_type
                if action_type == 'set_context_variable' and action_item_conf.variable_name is not None:
                    resolved_value = _resolve_value(action_item_conf.value_template, current_step_context, contact)
                    current_step_context[action_item_conf.variable_name] = resolved_value
                    logger.info(f"Contact {contact.id}: Action in step {step.id} set context var '{action_item_conf.variable_name}' to '{resolved_value}'.")
                elif action_type == 'update_contact_field' and action_item_conf.field_path is not None:
                    resolved_value = _resolve_value(action_item_conf.value_template, current_step_context, contact)
                    _update_contact_data(contact, action_item_conf.field_path, resolved_value)
                elif action_type == 'update_member_profile' and action_item_conf.fields_to_update is not None:
                    resolved_fields_to_update = _resolve_value(action_item_conf.fields_to_update, current_step_context, contact)
                    _update_member_profile_data(contact, resolved_fields_to_update, current_step_context)
                elif action_type == 'record_payment':
                    amount_str = _resolve_value(action_item_conf.amount_template, current_step_context, contact)
                    payment_type = _resolve_value(action_item_conf.payment_type_template, current_step_context, contact)
                    payment_method = _resolve_value(action_item_conf.payment_method_template, current_step_context, contact)
                    currency = _resolve_value(action_item_conf.currency_template, current_step_context, contact)
                    notes = _resolve_value(action_item_conf.notes_template, current_step_context, contact)
                    transaction_ref = _resolve_value(action_item_conf.transaction_ref_template, current_step_context, contact)
                    status = _resolve_value(action_item_conf.status_template, current_step_context, contact)
                    proof_of_payment_wamid = _resolve_value(action_item_conf.proof_of_payment_wamid_template, current_step_context, contact)

                    payment_obj, confirmation_action = record_payment(
                        contact=contact,
                        amount_str=str(amount_str) if amount_str is not None else "0",
                        payment_type=str(payment_type) if payment_type else "other",
                        payment_method=str(payment_method) if payment_method else "whatsapp_flow",
                        status=str(status) if status else None,
                        currency=str(currency) if currency else "USD",
                        notes=str(notes) if notes else None,
                        transaction_ref=str(transaction_ref) if transaction_ref else None,
                        proof_of_payment_wamid=str(proof_of_payment_wamid) if proof_of_payment_wamid else None
                    )

                    if payment_obj:
                        current_step_context['last_payment_id'] = str(payment_obj.id)
                        # --- FIX: Explicitly trigger the background task to download the POP image ---
                        # If a proof of payment WAMID was provided, we must schedule the download task.
                        if proof_of_payment_wamid:
                            from customer_data.tasks import process_proof_of_payment_image
                            # Use transaction.on_commit to ensure the task runs only after the payment is saved.
                            transaction.on_commit(lambda: process_proof_of_payment_image.delay(str(payment_obj.id), proof_of_payment_wamid))
                        logger.info(f"Contact {contact.id}: Action in step {step.id} recorded payment {payment_obj.id}.")
                        if confirmation_action:
                            actions_to_perform.append(confirmation_action)
                    else:
                        logger.error(f"Contact {contact.id}: Action in step {step.id} failed to record payment for amount '{amount_str}'.")
                
                elif action_type == 'initiate_paynow_giving_payment':
                    amount_str = _resolve_value(action_item_conf.amount_template, current_step_context, contact)
                    payment_type = _resolve_value(action_item_conf.payment_type_template, current_step_context, contact)
                    payment_method = _resolve_value(action_item_conf.payment_method_template, current_step_context, contact)
                    phone_number = _resolve_value(action_item_conf.phone_number_template, current_step_context, contact)
                    email = _resolve_value(action_item_conf.email_template, current_step_context, contact)
                    currency = _resolve_value(action_item_conf.currency_template, current_step_context, contact)
                    notes = _resolve_value(action_item_conf.notes_template, current_step_context, contact)

                    context_updates = _initiate_paynow_payment(contact, amount_str, payment_type, payment_method, phone_number, email, currency, notes)
                    current_step_context.update(context_updates)
                    logger.info(f"Contact {contact.id}: Action in step {step.id} initiated Paynow payment. Context updated: {context_updates}")

                elif action_type == 'record_prayer_request':
                    request_text = _resolve_value(action_item_conf.request_text_template, current_step_context, contact)
                    category = _resolve_value(action_item_conf.category_template, current_step_context, contact)
                    is_anonymous_val = _resolve_value(action_item_conf.is_anonymous_template, current_step_context, contact)
                    submitted_as_member_val = _resolve_value(action_item_conf.submitted_as_member_template, current_step_context, contact)

                    # Coerce resolved value to boolean
                    is_anonymous = str(is_anonymous_val).lower() in ['true', '1', 'yes'] if is_anonymous_val is not None else False
                    submitted_as_member = str(submitted_as_member_val).lower() in ['true', '1', 'yes'] if submitted_as_member_val is not None else False

                    prayer_request_obj = record_prayer_request(
                        contact=contact,
                        request_text=str(request_text) if request_text else "",
                        category=str(category) if category else "other",
                        is_anonymous=is_anonymous,
                        submitted_as_member=submitted_as_member
                    )
                    if prayer_request_obj:
                        current_step_context['last_prayer_request_id'] = str(prayer_request_obj.id)
                        logger.info(f"Contact {contact.id}: Action in step {step.id} recorded prayer request {prayer_request_obj.id}.")
                    else:
                        logger.error(f"Contact {contact.id}: Action in step {step.id} failed to record prayer request for text '{str(request_text)[:50]}...'.")
                elif action_type == 'record_event_booking':
                    event_id = _resolve_value(action_item_conf.event_id_template, current_step_context, contact)
                    number_of_tickets = _resolve_value(action_item_conf.number_of_tickets_template, current_step_context, contact)
                    status = _resolve_value(action_item_conf.status_template, current_step_context, contact)
                    notes = _resolve_value(action_item_conf.notes_template, current_step_context, contact)
                    proof_of_payment_wamid = _resolve_value(action_item_conf.proof_of_payment_wamid_template, current_step_context, contact)
                    event_fee_str = _resolve_value(current_step_context.get('event_fee'), current_step_context, contact)
                    event_fee = Decimal(event_fee_str) if event_fee_str else None
                    event_title = _resolve_value(current_step_context.get('event_title'), current_step_context, contact)

                    booking_obj, context_updates = record_event_booking(
                        contact=contact,
                        event_id=event_id,
                        num_tickets=int(number_of_tickets) if number_of_tickets else 1,
                        status=str(status) if status else 'confirmed',
                        notes=str(notes) if notes else None,
                        proof_of_payment_wamid=str(proof_of_payment_wamid) if proof_of_payment_wamid else None,
                        event_fee=event_fee,
                        event_title=str(event_title) if event_title else None
                    )
                    if booking_obj:
                        current_step_context.update(context_updates)
                        logger.info(f"Contact {contact.id}: Action in step {step.id} processed event booking {booking_obj.id}. Context updated.")
                    else:
                        current_step_context.update(context_updates)
                        logger.error(f"Contact {contact.id}: Action in step {step.id} failed to record event booking for event ID '{event_id}'.")
                elif action_type == 'send_admin_notification':
                    message_body = _resolve_value(action_item_conf.message_template, current_step_context, contact)
                    if not message_body:
                        logger.warning(f"Contact {contact.id}: 'send_admin_notification' message_template resolved to an empty string. Skipping.")
                        continue
                    
                    notify_groups = action_item_conf.notify_groups
                    notify_user_ids = action_item_conf.notify_user_ids

                    if notify_groups or notify_user_ids:
                        queue_notifications_to_users(
                            user_ids=action_item_conf.notify_user_ids,
                            group_names=action_item_conf.notify_groups,
                            message_body=message_body,
                            related_contact=contact,
                            related_flow=step.flow
                        )
                    else:
                        # Fallback to old behavior if no users are targeted
                        admin_number = settings.ADMIN_WHATSAPP_NUMBER
                        if admin_number:
                            message_body = _resolve_value(action_item_conf.message_template, current_step_context, contact)
                            if message_body:
                                actions_to_perform.append({'type': 'send_whatsapp_message', 'recipient_wa_id': admin_number, 'message_type': 'text', 'data': {'body': message_body}})
                                logger.info(f"Contact {contact.id}: Queued admin notification to fallback ADMIN_WHATSAPP_NUMBER {admin_number}.")
                        else:
                            logger.warning(f"Contact {contact.id}: 'send_admin_notification' action used, but no target users found and ADMIN_WHATSAPP_NUMBER is not set. Skipping.")
                elif action_type == 'query_model':
                    app_label = action_item_conf.app_label
                    model_name = action_item_conf.model_name
                    variable_name = action_item_conf.variable_name
                    
                    if not app_label or not model_name or not variable_name:
                        logger.error(f"Contact {contact.id}: 'query_model' action in step {step.id} is missing required fields. Skipping.")
                        continue
                    
                    try:
                        Model = apps.get_model(app_label, model_name)
                        
                        filters = _resolve_value(action_item_conf.filters_template, current_step_context, contact)
                        if not isinstance(filters, dict):
                            logger.warning(f"Contact {contact.id}: 'filters_template' for query_model did not resolve to a dictionary. Using empty filters. Resolved value: {filters}")
                            filters = {}
                            
                        # --- IMPROVEMENT: Automatically find and prefetch related objects (N+1 fix) ---
                        # This makes queries more efficient and allows templates to access related fields.
                        related_fields_to_select = []
                        related_fields_to_prefetch = []
                        for field in Model._meta.get_fields():
                            # Use select_related for single-object relationships (ForeignKey, OneToOne)
                            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                                related_fields_to_select.append(field.name)
                            # Use prefetch_related for many-to-many or reverse foreign key relationships
                            elif isinstance(field, (models.ManyToManyField, models.ManyToOneRel)):
                                related_fields_to_prefetch.append(field.name)
                        
                        queryset = Model.objects.filter(**filters)
                        if related_fields_to_select:
                            queryset = queryset.select_related(*related_fields_to_select)
                        if related_fields_to_prefetch:
                            queryset = queryset.prefetch_related(*related_fields_to_prefetch)
                        
                        order_by_fields = action_item_conf.order_by
                        if order_by_fields and isinstance(order_by_fields, list):
                            queryset = queryset.order_by(*order_by_fields)
                            
                        if action_item_conf.limit is not None and isinstance(action_item_conf.limit, int):
                            queryset = queryset[:action_item_conf.limit]
                            
                        results_list = []
                        for obj in queryset:
                            # Use a more robust serialization that includes related objects
                            dict_obj = {}
                            for field in obj._meta.fields:
                                dict_obj[field.name] = getattr(obj, field.name)
                            # Add selected (single) related objects as nested dictionaries
                            for related_field_name in related_fields_to_select:
                                related_obj = getattr(obj, related_field_name, None)
                                if related_obj:
                                    dict_obj[related_field_name] = model_to_dict(related_obj)
                            # Note: Prefetched (many) related objects are not easily serialized into this dict
                            # but the template can now access them without extra queries, which is the main goal.
                            # e.g. `{{ my_model.my_many_to_many_set.all() }}` in a template will be efficient.


                            # --- FIX: Recursively make the dictionary JSON serializable ---
                            def make_serializable(d):
                                for k, v in d.items():
                                    if isinstance(v, dict):
                                        make_serializable(v)
                                    elif isinstance(v, (datetime, date)):
                                        d[k] = v.isoformat()
                                    elif isinstance(v, models.fields.files.FieldFile):
                                        d[k] = v.url if v else None
                                    elif isinstance(v, Decimal):
                                        d[k] = str(v)
                                    elif isinstance(v, uuid.UUID):
                                        d[k] = str(v)
                            
                            make_serializable(dict_obj)
                            
                            results_list.append(dict_obj)
                            
                        current_step_context[variable_name] = results_list
                        logger.info(f"Contact {contact.id}: Action in step {step.id} queried {model_name} and stored {len(results_list)} items in '{variable_name}'.")
                    except LookupError:
                        logger.error(f"Contact {contact.id}: 'query_model' action in step {step.id} failed. Model '{app_label}.{model_name}' not found.")
                    except Exception as e:
                        logger.error(f"Contact {contact.id}: 'query_model' action in step {step.id} failed with error: {e}", exc_info=True)
                elif action_type == 'update_model_record':
                    app_label = action_item_conf.app_label
                    model_name = action_item_conf.model_name
                    if not app_label or not model_name:
                        logger.error(f"Contact {contact.id}: 'update_model_record' action in step {step.id} is missing 'app_label' or 'model_name'. Skipping.")
                        continue
                    try:
                        Model = apps.get_model(app_label, model_name)
                        filters = _resolve_value(action_item_conf.filters_template, current_step_context, contact)
                        updates = _resolve_value(action_item_conf.updates_template, current_step_context, contact)
                        updated_count = Model.objects.filter(**filters).update(**updates)
                        logger.info(f"Contact {contact.id}: Action in step {step.id} updated {updated_count} record(s) in {model_name} with filters {filters}.")
                    except LookupError:
                        logger.error(f"Contact {contact.id}: 'update_model_record' action in step {step.id} failed. Model '{app_label}.{model_name}' not found.")
                    except Exception as e:
                        logger.error(f"Contact {contact.id}: 'query_model' action in step {step.id} failed with error: {e}", exc_info=True)
                else:
                    logger.warning(f"Contact {contact.id}: Unknown or misconfigured action_type '{action_type}' in step '{step.name}' (ID: {step.id}).")
        except ValidationError as e:
            logger.error(f"Contact {contact.id}: Pydantic validation for 'action' step '{step.name}' (ID: {step.id}) failed: {e.errors()}", exc_info=False)

    elif step.step_type == 'switch_flow':
        try:
            switch_config = StepConfigSwitchFlow.model_validate(raw_step_config)
            
            # Start with the initial context from the config and resolve any templates in it
            initial_context = _resolve_value(switch_config.initial_context_template or {}, current_step_context, contact)
            if not isinstance(initial_context, dict):
                initial_context = {}

            # If a keyword is specified, add it to the context being passed to the new flow
            if switch_config.trigger_keyword_to_pass:
                initial_context['simulated_trigger_keyword'] = switch_config.trigger_keyword_to_pass

            actions_to_perform.append({
                'type': '_internal_command_switch_flow',
                'target_flow_name': switch_config.target_flow_name,
                'initial_context': initial_context
            })
            logger.info(f"Contact {contact.id}: Step '{step.name}' queued switch to flow '{switch_config.target_flow_name}'.")
        except ValidationError as e:
            logger.error(f"Contact {contact.id}: Pydantic validation for 'switch_flow' step '{step.name}' (ID: {step.id}) failed: {e.errors()}", exc_info=False)

    elif step.step_type == 'end_flow':
        try:
            end_flow_config = StepConfigEndFlow.model_validate(raw_step_config)
            if end_flow_config.message_config:
                try:
                    final_msg_pydantic_config = StepConfigSendMessage.model_validate(end_flow_config.message_config)
                    dummy_end_msg_step = FlowStep(name=f"{step.name}_final_msg", step_type="send_message", config=final_msg_pydantic_config.model_dump(exclude_none=True))
                    send_actions, _ = _execute_step_actions(dummy_end_msg_step, contact, current_step_context, request=request)
                    actions_to_perform.extend(send_actions)
                except ValidationError as ve:
                     logger.error(f"Contact {contact.id}: Pydantic validation for 'message_config' in 'end_flow' step '{step.name}' (ID: {step.id}): {ve.errors()}", exc_info=False)
            logger.info(f"Contact {contact.id}: Executing 'end_flow' step '{step.name}' (ID: {step.id}).")
            actions_to_perform.append({'type': '_internal_command_clear_flow_state'})
        except ValidationError as e:
            logger.error(f"Contact {contact.id}: Pydantic validation for 'end_flow' step '{step.name}' (ID: {step.id}) config: {e.errors()}", exc_info=False)

    elif step.step_type == 'human_handover':
        try:
            handover_config = StepConfigHumanHandover.model_validate(raw_step_config)
            logger.info(f"Contact {contact.id}: Executing 'human_handover' step '{step.name}'.")
            if handover_config.pre_handover_message_text and not is_re_execution: # Avoid sending pre-handover message on re-execution/fallback
                resolved_msg = _resolve_value(handover_config.pre_handover_message_text, current_step_context, contact)
                actions_to_perform.append({'type': 'send_whatsapp_message', 'recipient_wa_id': contact.whatsapp_id, 'message_type': 'text', 'data': {'body': resolved_msg}})
            
            # Flag for human intervention and record the exact time
            contact.needs_human_intervention = True
            intervention_time = timezone.now()
            contact.intervention_requested_at = intervention_time # Set timestamp
            # Save last_seen as well, since this is an interaction
            contact.save(update_fields=['needs_human_intervention', 'intervention_requested_at', 'last_seen'])
            logger.info(f"Contact {contact.id} ({contact.whatsapp_id}) flagged for human intervention via step '{step.name}' at {intervention_time.isoformat()}.")

            # Schedule the timeout task to run in 5 minutes
            timeout_seconds = 5 * 60
            resolve_human_intervention_after_timeout.apply_async(
                args=[contact.id, intervention_time.isoformat()],
                countdown=timeout_seconds
            )
            logger.info(f"Scheduled human intervention timeout task for contact {contact.id} in {timeout_seconds} seconds (triggered by step '{step.name}').")

            # Send notification to admin/pastoral groups
            # --- Enhanced Notification Details ---
            # If a detailed template is provided, use it. Otherwise, create a default one.
            if handover_config.notification_details:
                notification_info = _resolve_value(handover_config.notification_details, current_step_context, contact)
            else:
                # Build a default, informative notification if one isn't specified in the flow
                user_reply = current_step_context.get('last_user_message', 'N/A')
                
                # Sanitize context for display, removing internal keys
                context_to_display = {k: v for k, v in current_step_context.items() if not k.startswith('_')}
                context_str = json.dumps(context_to_display, indent=2, default=str) if context_to_display else "Empty"
                if len(context_str) > 1000: # Truncate for readability
                    context_str = context_str[:1000] + "\n... (truncated)"

                notification_info = (
                    f"⚠️ *Human Handover Required* ⚠️\n\n"
                    f"*Contact:* {contact.name or contact.whatsapp_id}\n"
                    f"*Flow:* {current_step_context.get('original_flow_name', step.flow.name)}\n"
                    f"*Step:* {current_step_context.get('original_step_name', step.name)}\n\n"
                    f"*Last User Input:*\n`{user_reply}`\n\n"
                    f"*Current Flow Context:*\n```\n{context_str}\n```"
                )

            if handover_config.notify_groups:
                queue_notifications_to_users(
                    group_names=handover_config.notify_groups,
                    message_body=notification_info,
                    related_contact=contact,
                    related_flow=step.flow # Use the flow from the current step
                )
                logger.info(f"Queued human intervention notification for groups {handover_config.notify_groups}.")
            else:
                logger.warning(f"Human handover for contact {contact.id} triggered, but no 'notify_groups' configured in step '{step.name}'.")

            actions_to_perform.append({'type': '_internal_command_clear_flow_state'})

        except ValidationError as e:
            logger.error(f"Contact {contact.id}: Pydantic validation for 'human_handover' step '{step.name}' (ID: {step.id}) failed: {e.errors()}", exc_info=False)
            # Send an error to the user and clear state to prevent getting stuck
            actions_to_perform.append({'type': 'send_whatsapp_message', 'recipient_wa_id': contact.whatsapp_id, 'message_type': 'text', 'data': {'body': "I'm sorry, I've encountered a system error while trying to connect you. Please type 'menu' to start again."}})
            actions_to_perform.append({'type': '_internal_command_clear_flow_state'})
        except Exception as e:
            logger.error(f"Contact {contact.id}: Unexpected error in 'human_handover' step '{step.name}': {e}", exc_info=True)
            actions_to_perform.append({'type': 'send_whatsapp_message', 'recipient_wa_id': contact.whatsapp_id, 'message_type': 'text', 'data': {'body': "I'm sorry, I've encountered a system error while trying to connect you. Please type 'menu' to start again."}})
            actions_to_perform.append({'type': '_internal_command_clear_flow_state'})

    elif step.step_type in ['condition', 'wait_for_reply', 'start_flow_node']: # 'wait_for_reply' is more a state than an executable step here
        logger.debug(f"'{step.step_type}' step '{step.name}' processed. No direct actions from this function, logic handled by transitions or flow control.")
    else:
        logger.warning(f"Unhandled step_type: '{step.step_type}' for step '{step.name}'.")

    return actions_to_perform, current_step_context
    

def _handle_fallback(current_step: FlowStep, contact: Contact, flow_context: dict, contact_flow_state: ContactFlowState, message_data: dict) -> List[Dict[str, Any]]:
    """
    Handles the logic when no transition condition is met from a step.
    This can be due to an invalid user reply to a question, or a logical dead-end in the flow.
    """
    actions_to_perform = []
    updated_context = flow_context.copy()
    try:
        # --- New Fallback Logic ---
        # Instead of complex logic here, we switch to a dedicated fallback flow.
        # This makes the system more modular and user-friendly.
        
        logger.info(f"Contact {contact.id}: Invalid input for step '{current_step.name}'. Switching to invalid_input_flow.")

        # We need to preserve the original context and details to potentially return to this step.
        # We remove internal keys that shouldn't be passed between flows.
        original_context_for_switch = {k: v for k, v in updated_context.items() if not k.startswith('_')}

        # Prepare the context for the invalid_input_flow
        initial_context_for_fallback_flow = {
            "original_flow_name": current_step.flow.name,
            "original_step_name": current_step.name,
            "original_context": original_context_for_switch,
            "last_user_message": message_data.get('text', {}).get('body', '[non-text message]')
        }

        # Create the internal command to switch to the fallback flow
        actions_to_perform.append({
            'type': '_internal_command_switch_flow',
            'target_flow_name': 'invalid_input_flow',
            'initial_context': initial_context_for_fallback_flow
        })

        return actions_to_perform

    except ValidationError as e:
        logger.warning(f"Invalid fallback_config for step {current_step.id}. Using defaults. Errors: {e.errors()}")
    except Exception as e:
        logger.error(f"CRITICAL: Error during fallback handling for contact {contact.id} at step {current_step.id}. Error: {e}", exc_info=True)
        # As a last resort, clear state and notify user of a system error.
        actions_to_perform.append({'type': '_internal_command_clear_flow_state'})
        actions_to_perform.append({
            'type': 'send_whatsapp_message', 'recipient_wa_id': contact.whatsapp_id,
            'message_type': 'text', 'data': {'body': "I'm sorry, I've encountered a system error. Please type 'menu' to start again."}
        })
        return actions_to_perform

def _trigger_new_flow(contact: Contact, message_data: dict, incoming_message_obj: Message, request: Optional[HttpRequest] = None) -> bool:
    """
    Finds and sets up the initial state for a new flow based on a trigger keyword.
    This function does NOT execute the first step; it only creates the state.
    The main processing loop is responsible for all step executions. The request object
    is passed along to be available for step execution context.

    Returns:
        True if a flow was triggered, False otherwise.
    """
    # --- FIX: Check for simulated keyword in both message data and initial context ---
    # The `simulated_trigger_keyword` can come from a user message (legacy) or be passed
    # in the context during a flow switch (e.g., from invalid_input_flow).
    message_text_body = None
    if message_data.get('type') == 'text':
        message_text_body = message_data.get('text', {}).get('body', '').lower().strip()

    # The incoming_message_obj can carry context from a flow switch action.
    initial_context_from_switch = getattr(incoming_message_obj, 'flow_context_data', {})
    simulated_keyword = initial_context_from_switch.get('simulated_trigger_keyword')

    # The keyword can be in the message body OR in the context from a switch.
    # This makes the "reprompt" feature work from the invalid_input_flow.
    trigger_keyword_source = simulated_keyword or message_text_body

    triggered_flow = None
    active_flows = Flow.objects.filter(is_active=True).order_by('name')

    if message_text_body:  # Only attempt keyword trigger if there's text
        for flow_candidate in active_flows:
            if isinstance(flow_candidate.trigger_keywords, list):
                # --- New Reprompt Logic ---
                # Check for a special "reprompt" keyword from the invalid_input_flow
                # e.g., "reprompt_step_ask_for_amount"
                reprompt_prefix = "reprompt_step_"
                if trigger_keyword_source and trigger_keyword_source.startswith(reprompt_prefix):
                    step_name_to_reprompt = trigger_keyword_source[len(reprompt_prefix):]
                    # Find the step in the current candidate flow
                    reprompt_step = flow_candidate.steps.filter(name=step_name_to_reprompt).first()
                    if reprompt_step:
                        return _setup_flow_at_specific_step(contact, flow_candidate, reprompt_step, incoming_message_obj.flow_context_data)
                for keyword in flow_candidate.trigger_keywords:
                    # Ensure keyword is a non-empty string before lowercasing
                    if isinstance(keyword, str) and keyword.strip() and keyword.strip().lower() in message_text_body:
                        triggered_flow = flow_candidate
                        logger.info(f"Keyword '{keyword}' triggered flow '{flow_candidate.name}' for contact {contact.whatsapp_id}.")
                        break
            if triggered_flow:
                break

    if triggered_flow:
        entry_point_step = FlowStep.objects.filter(flow=triggered_flow, is_entry_point=True).first()
        if entry_point_step:
            return _setup_flow_at_specific_step(contact, triggered_flow, entry_point_step)
        else:
            logger.error(f"Flow '{triggered_flow.name}' is active but has no entry point step defined.")
            return False  # Failed to trigger
    else:
        logger.info(f"No active flow triggered for contact {contact.whatsapp_id} with message: {message_text_body[:100] if message_text_body else message_data.get('type')}")
        return False # No flow triggered

def _setup_flow_at_specific_step(contact: Contact, flow: Flow, step: FlowStep, initial_context: dict = None) -> bool:
    """Helper to set up a contact's flow state at a specific step."""
    logger.info(
        f"Setting up flow '{flow.name}' for contact {contact.whatsapp_id} at step '{step.name}'. "
        f"Initial context: {'Exists' if initial_context else 'Empty'}"
    )

    # Clear any existing flow state before starting a new one.
    _clear_contact_flow_state(contact)

    ContactFlowState.objects.create(
        contact=contact,
        current_flow=flow,
        current_step=step,
        flow_context_data=initial_context or {},
        started_at=timezone.now()
    )
    return True  # Successfully triggered


def _evaluate_transition_condition(transition: FlowTransition, contact: Contact, message_data: dict, flow_context: dict, incoming_message_obj: Message) -> bool:
    config = transition.condition_config
    if not isinstance(config, dict):
        logger.warning(f"Transition {transition.id} has invalid condition_config (not a dict): {config}")
        return False
    condition_type = config.get('type')
    logger.debug(f"Contact {contact.id}, Flow {transition.current_step.flow.id}, Step {transition.current_step.id}: Evaluating condition type '{condition_type}' for transition {transition.id}. Context: {flow_context}, Message Type: {message_data.get('type')}")

    if not condition_type: return False # No condition type means no specific condition to evaluate beyond default
    if condition_type == 'always_true': return True

    user_text = ""
    if message_data.get('type') == 'text' and isinstance(message_data.get('text'), dict):
        user_text = message_data.get('text', {}).get('body', '').strip()

    interactive_reply_id = None
    nfm_response_data = None 
    if message_data.get('type') == 'interactive' and isinstance(message_data.get('interactive'), dict):
        interactive_payload = message_data.get('interactive', {})
        interactive_type_from_payload = interactive_payload.get('type')
        if interactive_type_from_payload == 'button_reply' and isinstance(interactive_payload.get('button_reply'), dict):
            interactive_reply_id = interactive_payload.get('button_reply', {}).get('id')
        elif interactive_type_from_payload == 'list_reply' and isinstance(interactive_payload.get('list_reply'), dict):
            interactive_reply_id = interactive_payload.get('list_reply', {}).get('id')
        elif interactive_type_from_payload == 'nfm_reply' and isinstance(interactive_payload.get('nfm_reply'), dict):
            nfm_payload = interactive_payload.get('nfm_reply', {})
            response_json_str = nfm_payload.get('response_json')
            if response_json_str:
                try: nfm_response_data = json.loads(response_json_str)
                except json.JSONDecodeError: logger.warning(f"Could not parse nfm_reply response_json for transition {transition.id}")
    
    # --- Condition Implementations ---
    value_for_condition = config.get('value') # Get expected value for comparison

    if condition_type == 'user_reply_matches_keyword':
        keyword = str(config.get('keyword', '')).strip()
        if not keyword: return False # Cannot match empty keyword
        case_sensitive = config.get('case_sensitive', False)
        return (keyword == user_text) if case_sensitive else (keyword.lower() == user_text.lower())
    
    elif condition_type == 'user_reply_contains_keyword':
        keyword = str(config.get('keyword', '')).strip()
        if not keyword: return False
        case_sensitive = config.get('case_sensitive', False)
        return (keyword in user_text) if case_sensitive else (keyword.lower() in user_text.lower())
    
    elif condition_type == 'interactive_reply_id_equals':
        return interactive_reply_id is not None and interactive_reply_id == str(value_for_condition)
    
    elif condition_type == 'message_type_is':
        return message_data.get('type') == str(value_for_condition) # Compare with expected message_type
    
    elif condition_type == 'user_reply_matches_regex':
        regex = config.get('regex')
        if regex and user_text:
            try: return bool(re.match(regex, user_text))
            except re.error as e: logger.error(f"Invalid regex in transition {transition.id}: {regex}. Error: {e}"); return False
        return False
        
    elif condition_type == 'variable_equals':
        variable_name = config.get('variable_name')
        if variable_name is None: return False
        actual_value = _get_value_from_context_or_contact(variable_name, flow_context, contact)
        # Compare as strings for simplicity and predictability in flow logic
        result = str(actual_value) == str(value_for_condition)
        logger.debug(
            f"Contact {contact.id}, Flow {transition.current_step.flow.id}, Step {transition.current_step.id}: "
            f"Condition 'variable_equals' check for '{variable_name}'. "
            f"Actual: '{actual_value}' (type: {type(actual_value).__name__}), "
            f"Expected: '{value_for_condition}' (type: {type(value_for_condition).__name__}). "
            f"Result (str comparison): {result}"
        )
        return result
        
    elif condition_type == 'variable_exists':
        variable_name_template = config.get('variable_name')
        if variable_name_template is None: return False
        # Resolve the variable name itself as a template to handle dynamic paths like 'list.{{ index }}'
        resolved_variable_path = _resolve_value(variable_name_template, flow_context, contact)
        
        # --- FIX: More robust check for list index existence ---
        # Jinja's default behavior for an out-of-bounds index is to return an empty string or SilentUndefined.
        # We need to differentiate this from a variable that genuinely exists but is empty.
        # By temporarily changing the Undefined handler, we can catch the specific UndefinedError.
        jinja_env.undefined = Undefined # Temporarily use the default, which raises an error
        try:
            actual_value = _get_value_from_context_or_contact(resolved_variable_path, flow_context, contact)
            # An empty string from Jinja often means the path resolved but the value is empty.
            # For 'variable_exists', we must treat an empty string as non-existent to correctly
            # differentiate between a missing profile and a profile with an empty field.
            result = actual_value is not None and actual_value != ''
        except Exception: # Catches UndefinedError from Jinja when the path is invalid
            result = False
        finally:
            jinja_env.undefined = SilentUndefined # Always restore our custom handler

        logger.debug(
            f"Contact {contact.id}, Flow {transition.current_step.flow.id}, Step {transition.current_step.id}: "
            f"Condition 'variable_exists' check for '{resolved_variable_path}'. "
            f"Result: {result}"
        )
        return result
        
    elif condition_type == 'variable_contains':
        variable_name = config.get('variable_name')
        if variable_name is None: return False
        actual_value = _get_value_from_context_or_contact(variable_name, flow_context, contact)
        expected_item = value_for_condition # This is the 'value' field from config
        result = False
        if isinstance(actual_value, str) and isinstance(expected_item, str): result = expected_item in actual_value
        elif isinstance(actual_value, list) and expected_item is not None: result = expected_item in actual_value
        
        logger.debug(
            f"Contact {contact.id}, Flow {transition.current_step.flow.id}, Step {transition.current_step.id}: "
            f"Condition 'variable_contains' check for '{variable_name}'. "
            f"Container: '{str(actual_value)[:100]}' (type: {type(actual_value).__name__}), "
            f"Expected item: '{expected_item}'. Result: {result}"
        )
        return result

    elif condition_type == 'variable_less_than':
        variable_name = config.get('variable_name')
        if variable_name is None: return False
        actual_value = _get_value_from_context_or_contact(variable_name, flow_context, contact)
        expected_value = _resolve_value(value_for_condition, flow_context, contact)
        try:
            # Attempt to convert both to floats for a numeric comparison
            result = float(actual_value) < float(expected_value)
            logger.debug(
                f"Contact {contact.id}, Flow {transition.current_step.flow.id}, Step {transition.current_step.id}: "
                f"Condition 'variable_less_than' check for '{variable_name}'. "
                f"Actual: '{actual_value}', Expected < '{expected_value}'. Result: {result}"
            )
            return result
        except (ValueError, TypeError):
            logger.warning(f"Could not perform 'variable_less_than' comparison for contact {contact.id}. "
                           f"Could not convert '{actual_value}' or '{expected_value}' to float.")
            return False
    elif condition_type == 'variable_greater_than':
        variable_name = config.get('variable_name')
        if variable_name is None: return False
        actual_value = _get_value_from_context_or_contact(variable_name, flow_context, contact)
        try:
            # Attempt to convert both to floats for a numeric comparison
            result = float(actual_value) > float(value_for_condition)
            logger.debug(
                f"Contact {contact.id}, Flow {transition.current_step.flow.id}, Step {transition.current_step.id}: "
                f"Condition 'variable_greater_than' check for '{variable_name}'. "
                f"Actual: '{actual_value}', Expected >: '{value_for_condition}'. Result: {result}"
            )
            return result
        except (ValueError, TypeError):
            logger.warning(f"Could not perform 'variable_greater_than' comparison for contact {contact.id}. "
                           f"Could not convert '{actual_value}' or '{value_for_condition}' to float.")
            return False

    elif condition_type == 'nfm_response_field_equals' and nfm_response_data:
        field_path = config.get('field_path')
        if not field_path: return False
        actual_val_from_nfm = nfm_response_data
        for part in field_path.split('.'):
            if isinstance(actual_val_from_nfm, dict): actual_val_from_nfm = actual_val_from_nfm.get(part)
            else: actual_val_from_nfm = None; break
        return actual_val_from_nfm == value_for_condition

    elif condition_type == 'question_reply_is_valid':
        # This condition is now implicitly handled by the logic within _handle_active_flow_step
        # when it processes a reply for a question. If flow_context has the saved variable,
        # it means the reply was valid according to the question's own reply_config.
        # The transition would then typically check if that variable_exists or variable_equals.
        # However, to directly use this condition type, we'd need to re-evaluate validity here.
        # For now, assume a question step saves valid reply to context, then use 'variable_exists'
        # or 'variable_equals' on the saved variable in the transition.
        # If value_for_condition is True, check if the specific variable for the current question (if any) was set.
        question_expectation = flow_context.get('_question_awaiting_reply_for')
        if question_expectation and isinstance(question_expectation, dict):
            var_name = question_expectation.get('variable_name')
            # If value is True, we check if the variable was set (implying valid reply)
            # If value is False, we check if the variable was *not* set (implying invalid reply)
            is_var_set = var_name in flow_context
            return is_var_set if value_for_condition is True else not is_var_set
        return False # No question was being awaited or config mismatch

    elif condition_type == 'user_requests_human':
        human_request_keywords = config.get('keywords', ['help', 'support', 'agent', 'human', 'operator'])
        if user_text and isinstance(human_request_keywords, list):
            user_text_lower = user_text.lower()
            for keyword in human_request_keywords:
                if isinstance(keyword, str) and keyword.strip() and keyword.strip().lower() in user_text_lower:
                    logger.info(f"User requested human agent with keyword: '{keyword}'")
                    return True
        return False

    logger.warning(f"Unknown or unhandled condition type: '{condition_type}' for transition {transition.id} or condition logic not met.")
    return False


def _transition_to_step(contact_flow_state: ContactFlowState, next_step: FlowStep, current_flow_context: dict, contact: Contact, message_data: dict, request: Optional[HttpRequest] = None) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    logger.info(f"Transitioning contact {contact.whatsapp_id} from '{contact_flow_state.current_step.name}' to '{next_step.name}' in flow '{contact_flow_state.current_flow.name}'.")
    
    # Clear question-specific context from the *previous* step if it was a question
    if contact_flow_state.current_step.step_type == 'question':
        current_flow_context.pop('_question_awaiting_reply_for', None)
        current_flow_context.pop('_fallback_count', None)
        logger.debug(f"Cleared question expectation and fallback count from previous step '{contact_flow_state.current_step.name}'.")

    # --- FIX: Save the new step and the context from the previous step's answer ---
    # This ensures the contact is officially at the new step before we execute its actions.
    contact_flow_state.current_step = next_step
    contact_flow_state.flow_context_data = current_flow_context
    # Use transaction.atomic to ensure that the state update and subsequent actions
    # are treated as a single unit of work where possible.
    # The save() here commits the move to the new step.
    contact_flow_state.save()

    actions_from_new_step, context_after_new_step_execution = _execute_step_actions(
        next_step, contact, current_flow_context.copy(), request=request # Pass a copy to avoid modification by reference if new step also modifies
    )
    
    # Re-fetch state to see if it was cleared or changed by _execute_step_actions (e.g., by end_flow, human_handover, switch_flow)
    # This is a critical check for robustness.
    with transaction.atomic():
        current_db_state = ContactFlowState.objects.select_for_update().filter(contact=contact).first()

        if current_db_state and current_db_state.pk == contact_flow_state.pk:
            # If the state still exists and belongs to this flow, then save the context
            # that resulted from executing this 'next_step'.
            if current_db_state.flow_context_data != context_after_new_step_execution:
                current_db_state.flow_context_data = context_after_new_step_execution
                current_db_state.save(update_fields=['flow_context_data', 'last_updated_at'])
                logger.debug(f"Saved updated context for contact {contact.whatsapp_id} after executing step '{next_step.name}'.")
        elif not current_db_state:
            logger.info(f"ContactFlowState for contact {contact.whatsapp_id} was cleared during execution of step '{next_step.name}'. No final context to save.")
        else: # State exists but is different (e.g., switched flow)
            logger.info(f"ContactFlowState for contact {contact.whatsapp_id} changed during execution of step '{next_step.name}'. New state: {current_db_state}")
        
    return actions_from_new_step, context_after_new_step_execution


def _update_contact_data(contact: Contact, field_path: str, value_to_set: Any):
    if not field_path: 
        logger.warning("Empty field_path provided for _update_contact_data.")
        return
    
    # This logic is simple, but could be expanded to handle nested JSON fields on Contact if needed.
    parts = field_path.split('.')
    target_object = contact
    field_to_update_on_object = None
    
    if len(parts) == 1: # Direct attribute on Contact model
        field_name = parts[0]
        if field_name.lower() in ['id', 'pk', 'whatsapp_id']: # Protected fields
            logger.warning(f"Attempt to update protected Contact field '{field_name}' denied.")
            return
        try:
            if hasattr(contact, field_name):
                setattr(contact, field_name, value_to_set)
                contact.save(update_fields=[field_name])
                logger.info(f"Updated Contact {contact.whatsapp_id} field '{field_name}' to '{value_to_set}'.")
            else:
                logger.warning(f"Contact field '{field_name}' not found.")
        except (DjangoValidationError, TypeError) as e:
            logger.error(f"Failed to update Contact field '{field_name}' for contact {contact.id} with value '{value_to_set}'. Error: {e}", exc_info=False)

            
    elif parts[0] == 'custom_fields': # Handling nested updates in JSONField 'custom_fields'
        if not isinstance(contact.custom_fields, dict):
            contact.custom_fields = {} # Initialize if not a dict
        
        current_level = contact.custom_fields
        for i, key in enumerate(parts[1:-1]): # Navigate to the second to last key
            current_level = current_level.setdefault(key, {})
            if not isinstance(current_level, dict):
                logger.error(f"Path error in Contact.custom_fields: '{key}' is not a dict for path '{field_path}'.")
                return
        
        final_key = parts[-1]
        if len(parts) > 1 : # Ensure there's at least one key after 'custom_fields'
            current_level[final_key] = value_to_set
            contact.save(update_fields=['custom_fields'])
            logger.info(f"Updated Contact {contact.whatsapp_id} custom_fields path '{'.'.join(parts[1:])}' to '{value_to_set}'.")
        else: # Only 'custom_fields' was specified, meaning replace the whole dict
            if isinstance(value_to_set, dict):
                contact.custom_fields = value_to_set
                contact.save(update_fields=['custom_fields'])
                logger.info(f"Replaced Contact {contact.whatsapp_id} custom_fields with: {value_to_set}")
            else:
                logger.warning(f"Cannot replace Contact.custom_fields with a non-dictionary value for path '{field_path}'.")
    else:
        logger.warning(f"Unsupported field path '{field_path}' for updating Contact model.")


def _update_member_profile_data(contact: Contact, fields_to_update_config: Dict[str, Any], flow_context: dict):
    if not fields_to_update_config or not isinstance(fields_to_update_config, dict): 
        logger.warning("_update_member_profile_data called with invalid fields_to_update_config.")
        return

    # get_or_create is atomic and safe for concurrent requests.
    profile, created = MemberProfile.objects.get_or_create(contact=contact)
    if created: 
        logger.info(f"Created MemberProfile for contact {contact.whatsapp_id}")

    changed_fields = []
    for field_path, value_template in fields_to_update_config.items():
        resolved_value = _resolve_value(value_template, flow_context, contact) # Resolve value using context
        
        # Handle 'skip' for optional fields by setting them to None
        if isinstance(resolved_value, str) and resolved_value.lower() == 'skip':
            resolved_value = None
        
        parts = field_path.split('.')
        if len(parts) == 1: # Direct attribute on MemberProfile model
            field_name = parts[0]
            # Prevent updating protected/internal fields
            if hasattr(profile, field_name) and field_name.lower() not in ['id', 'pk', 'contact', 'contact_id', 'created_at', 'updated_at', 'last_updated_from_conversation']:
                try:
                    field_object = profile._meta.get_field(field_name)
                    # Robustness: Coerce empty strings to None for nullable fields to prevent validation errors.
                    if isinstance(field_object, models.DateField) and resolved_value == '':
                        resolved_value = None

                    setattr(profile, field_name, resolved_value)
                    if field_name not in changed_fields: 
                        changed_fields.append(field_name)
                except (DjangoValidationError, TypeError, ValueError) as e:
                    logger.error(f"Validation/Type error updating MemberProfile field '{field_name}' for contact {contact.id} with value '{resolved_value}'. Error: {e}", exc_info=False)
                    # Continue to next field, do not add to changed_fields
                    continue
            else:
                logger.warning(f"MemberProfile field '{field_name}' not found or is protected.")
        elif parts[0] in ['preferences', 'custom_attributes'] and len(parts) > 1: # JSONFields
            json_field_name = parts[0]
            json_data = getattr(profile, json_field_name)
            if not isinstance(json_data, dict): 
                json_data = {} # Initialize if None or not a dict
            
            current_level = json_data
            for key in parts[1:-1]: # Navigate to the second to last key
                current_level = current_level.setdefault(key, {})
                if not isinstance(current_level, dict):
                    logger.warning(f"Path error in MemberProfile.{json_field_name} at '{key}'. Expected dict, found {type(current_level)}.")
                    current_level = None # Stop further processing for this path
                    break
            
            if current_level is not None:
                final_key = parts[-1]
                current_level[final_key] = resolved_value
                setattr(profile, json_field_name, json_data) # Assign the modified dict back
                if json_field_name not in changed_fields:
                    changed_fields.append(json_field_name)
        else:
            logger.warning(f"Unsupported field path for MemberProfile: {field_path}")

    if changed_fields:
        profile.last_updated_from_conversation = timezone.now()
        if 'last_updated_from_conversation' not in changed_fields:
            changed_fields.append('last_updated_from_conversation')
        profile.save(update_fields=changed_fields)
        logger.info(f"MemberProfile for {contact.whatsapp_id} updated fields: {changed_fields}")
    elif created: # If only created and no specific fields changed by the action, still update timestamp
        profile.last_updated_from_conversation = timezone.now()
        profile.save(update_fields=['last_updated_from_conversation'])



# --- Main Service Function (process_message_for_flow) ---
# This is the function that should be imported by meta_integration/views.py
@transaction.atomic
def process_message_for_flow(contact: Contact, message_data: dict, incoming_message_obj: Message, request: Optional[HttpRequest] = None) -> List[Dict[str, Any]]:
    """
    Main entry point to process an incoming message for a contact against flows.
    Determines if the contact is in an active flow or if a new flow should be triggered.
    """
    # --- Performance Optimization ---
    # Eagerly load the related member_profile to prevent N+1 queries during template/condition resolution.
    # This is a safe way to ensure the profile is available without modifying the calling view.
    try:
        contact = Contact.objects.select_related('member_profile').get(pk=contact.pk)
    except Contact.DoesNotExist:
        # This should theoretically not happen if the contact was just created/retrieved, but it's a safe guard.
        logger.error(f"Contact with pk={contact.pk} not found at start of flow processing. Aborting.")
        return []

    # If a contact is flagged for human intervention, pause all flow processing for them.
    # An admin or agent must manually clear this flag in the admin panel or CRM interface
    # to re-enable automated flows for this contact.
    if contact.needs_human_intervention:
        logger.info(
            f"Flow processing is paused for contact {contact.id} ({contact.whatsapp_id}) "
            "as they require human intervention. No automated actions will be taken."
        )
        # By returning an empty list, we stop any further flow logic from executing.
        return []

    actions_to_perform = []
    try:
        # --- Start of Main Flow Processing Loop ---
        # This loop will continue as long as the contact is in an active flow state.
        # It allows for "fall-through" steps (like 'action' steps) to be processed immediately.
        while True:
            is_internal_message = message_data.get('type', '').startswith('internal_')
            contact_flow_state = ContactFlowState.objects.select_related('current_flow', 'current_step').filter(contact=contact).first()

            if not contact_flow_state:
                logger.info(f"No active flow state for contact {contact.whatsapp_id}. Attempting to trigger a new flow.")
                
                # _trigger_new_flow now returns a boolean and handles state creation.
                flow_was_triggered = _trigger_new_flow(contact, message_data, incoming_message_obj, request=request)
                
                if flow_was_triggered:
                    # A new flow was started, re-run the loop to process its first step.
                    continue 
                else:
                    # No flow was triggered. Send a helpful default message to avoid a dead end.
                    logger.info(f"No flow triggered for contact {contact.whatsapp_id}. Sending default fallback message.")
                    actions_to_perform.append({
                        'type': 'send_whatsapp_message',
                        'recipient_wa_id': contact.whatsapp_id,
                        'message_type': 'text',
                        'data': {'body': "I'm sorry, I didn't understand that. Please type 'menu' to see what I can help you with."}
                    })
                    break 

            current_step = contact_flow_state.current_step
            flow_context = contact_flow_state.flow_context_data if contact_flow_state.flow_context_data is not None else {}

            logger.debug(f"Handling active flow. Contact: {contact.whatsapp_id}, Current Step: '{current_step.name}' (Type: {current_step.step_type}). Context: {flow_context}")

            # --- Step 1: Process incoming message if the current step is a question ---
            is_pass_through_step = True # Assume step is pass-through unless it's a question
            if current_step.step_type == 'question' and '_question_awaiting_reply_for' in flow_context:
                # If we've arrived at a question step via an internal transition (fallthrough/switch),
                # we must stop and wait for the user's actual reply. We should not process the
                # internal message as if it were a user's answer.
                if is_internal_message:
                    logger.debug(f"Reached question step '{current_step.name}' via internal transition. Breaking loop to await user reply.")
                    break
                is_pass_through_step = False # A question is NOT a pass-through step; it must wait for a reply.
                question_expectation = flow_context['_question_awaiting_reply_for']
                variable_to_save_name = question_expectation.get('variable_name')
                expected_reply_type = question_expectation.get('expected_type')
                validation_regex_ctx = question_expectation.get('validation_regex')
                
                user_text = message_data.get('text', {}).get('body', '').strip() if message_data.get('type') == 'text' else None
                interactive_reply_id = None
                if message_data.get('type') == 'interactive':
                    interactive_payload = message_data.get('interactive', {})
                    interactive_type = interactive_payload.get('type')
                    if interactive_type == 'button_reply':
                        interactive_reply_id = interactive_payload.get('button_reply', {}).get('id')
                    elif interactive_type == 'list_reply':
                        interactive_reply_id = interactive_payload.get('list_reply', {}).get('id')
                
                image_payload = message_data.get('image') if message_data.get('type') == 'image' else None

                reply_is_valid = False
                value_to_save = None

                if expected_reply_type == 'text' and user_text:
                    value_to_save = user_text; reply_is_valid = True
                elif expected_reply_type == 'email':
                    email_r = validation_regex_ctx or r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    if user_text and re.match(email_r, user_text):
                        value_to_save = user_text; reply_is_valid = True
                elif expected_reply_type == 'number' and user_text:
                    try:
                        value_to_save = float(user_text) if '.' in user_text or (validation_regex_ctx and '.' in validation_regex_ctx) else int(user_text)
                        reply_is_valid = True
                        if validation_regex_ctx and not re.match(validation_regex_ctx, str(value_to_save)):
                            reply_is_valid = False; value_to_save = None
                    except ValueError: pass
                elif expected_reply_type == 'interactive_id' and interactive_reply_id:
                    value_to_save = interactive_reply_id; reply_is_valid = True
                elif expected_reply_type == 'image' and image_payload:
                    value_to_save = image_payload.get('id') # Save the WhatsApp Media ID
                    if value_to_save:
                        reply_is_valid = True
                
                if validation_regex_ctx and not reply_is_valid and user_text and expected_reply_type == 'text':
                    if re.match(validation_regex_ctx, user_text):
                        value_to_save = user_text; reply_is_valid = True
                
                if reply_is_valid and variable_to_save_name:
                    flow_context[variable_to_save_name] = value_to_save
                    logger.info(f"Saved valid reply for '{variable_to_save_name}' in question step '{current_step.name}': {value_to_save}")
                    # Clear any previous fallback state since the reply is now valid
                    flow_context.pop('_question_awaiting_reply_for', None)
                    flow_context.pop('_fallback_count', None)
                else:
                    logger.info(f"Reply for question step '{current_step.name}' was not valid. Expected: {expected_reply_type}")
                    # --- FIX: Engage fallback immediately for invalid reply ---
                    actions_to_perform.extend(_handle_fallback(current_step, contact, flow_context, contact_flow_state, message_data))
                    break # Stop processing this message further; wait for new input.

            # --- Step 2: Evaluate transitions from the current step ---
            transitions = FlowTransition.objects.filter(current_step=current_step).select_related('next_step').order_by('priority')
            next_step_to_transition_to = None
            for transition in transitions:
                if _evaluate_transition_condition(transition, contact, message_data, flow_context, incoming_message_obj):
                    next_step_to_transition_to = transition.next_step
                    logger.info(f"Transition condition met: From '{current_step.name}' to '{next_step_to_transition_to.name}'.")
                    break
            
            if next_step_to_transition_to:
                actions, flow_context = _transition_to_step(contact_flow_state, next_step_to_transition_to, flow_context, contact, message_data, request=request)
                
                # Check for a switch_flow command specifically to handle it within the loop
                switch_action = next((a for a in actions if a.get('type') == '_internal_command_switch_flow'), None)
                if switch_action:
                    logger.info(f"Contact {contact.id}: Processing internal command to switch flow within the main loop.")
                    try:
                        _clear_contact_flow_state(contact) # Clear old state

                        new_flow_name = switch_action.get('target_flow_name')
                        initial_context_for_new_flow = switch_action.get('initial_context', {})

                        target_flow = Flow.objects.get(name=new_flow_name, is_active=True)
                        entry_point_step = FlowStep.objects.filter(flow=target_flow, is_entry_point=True).first()

                        if not entry_point_step:
                            raise ValueError(f"Flow '{new_flow_name}' is active but has no entry point step defined.")
                        
                        logger.info(f"Contact {contact.id}: Switching to flow '{target_flow.name}' at entry step '{entry_point_step.name}'.")
                        
                        new_contact_flow_state = ContactFlowState.objects.create(
                            contact=contact,
                            current_flow=target_flow,
                            current_step=entry_point_step,
                            flow_context_data=initial_context_for_new_flow,
                            started_at=timezone.now()
                        )

                        # --- FIX: Manually execute the actions for the new entry point step ---
                        # This ensures that 'action' steps at the start of a flow are run immediately
                        # after a switch, before the loop continues to evaluate transitions.
                        entry_actions, updated_context = _execute_step_actions(
                            entry_point_step, contact, initial_context_for_new_flow.copy(), request=request
                        )
                        actions_to_perform.extend(entry_actions)
                        
                        # Save the context after this first execution
                        new_contact_flow_state.flow_context_data = updated_context
                        new_contact_flow_state.save(update_fields=['flow_context_data', 'last_updated_at'])
                        logger.debug(f"Contact {contact.id}: Executed entry step '{entry_point_step.name}' and saved context.")

                        # --- FIX: Check if the new entry point immediately ended the flow ---
                        # If so, break the main loop to allow the clear_state command to be processed.
                        if any(action.get('type') == '_internal_command_clear_flow_state' for action in entry_actions):
                            break
                        
                        # The message is "consumed" by the first step that uses it.
                        # For subsequent automatic steps in the new flow, we need to prevent reprocessing the original message.
                        message_data = {'type': 'internal_switch_flow'}
                        incoming_message_obj = None
                        
                        continue # Restart the loop to process the new flow's entry point

                    except (Flow.DoesNotExist, ValueError) as e:
                        logger.error(f"Contact {contact.id}: Failed to switch flow to '{switch_action.get('target_flow_name')}'. Error: {e}", exc_info=True)
                        _clear_contact_flow_state(contact, error=True) # Ensure state is cleared on failure
                        actions_to_perform.append({
                            'type': 'send_whatsapp_message', 'recipient_wa_id': contact.whatsapp_id, 'message_type': 'text',
                            'data': {'body': 'I seem to be having some technical difficulties. Please try again in a moment.'}
                        })
                        break # Exit loop on failure
                else:
                    # No switch command, so process actions normally and check for other control commands
                    actions_to_perform.extend(actions)
                    if any(action.get('type') == '_internal_command_clear_flow_state' for action in actions):
                        break # Exit the while loop for end_flow or human_handover

            else:
                logger.info(f"No transition met for step '{current_step.name}'. Engaging fallback logic for contact {contact.id}.")
                fallback_actions = _handle_fallback(current_step, contact, flow_context, contact_flow_state, message_data)
                actions_to_perform.extend(fallback_actions)
                break # Fallback always breaks the loop

            # --- Step 3: Loop Control ---
            # If the new step is a question, or if the flow state was cleared (e.g., end_flow), break the loop.
            new_state = ContactFlowState.objects.filter(contact=contact).first()
            if not new_state or new_state.current_step.step_type in ['question', 'end_flow', 'human_handover']:
                break
            
            # The message_data is "consumed" by the first step that uses it (the question step).
            # For subsequent automatic "fall-through" steps, we use an empty message_data.
            message_data = {'type': 'internal_fallthrough'}
            incoming_message_obj = None
            is_internal_message = True
    except Exception as e:
        logger.error(f"Critical error in process_message_for_flow for contact {contact.whatsapp_id}: {e}", exc_info=True)
        # Clear state on unhandled error to prevent loops and allow re-triggering or human intervention
        _clear_contact_flow_state(contact, error=True)
        # Notify user of an issue
        actions_to_perform = [{ # Reset actions to only send an error message
            'type': 'send_whatsapp_message',
            'recipient_wa_id': contact.whatsapp_id,
            'message_type': 'text',
            'data': {'body': 'I seem to be having some technical difficulties. Please try again in a moment.'}
        }]

    # Process internal commands generated by _execute_step_actions or _handle_active_flow_step
    final_actions_for_meta_view = []
    for action in actions_to_perform: # actions_to_perform could be modified by switch_flow
        if action.get('type') == '_internal_command_clear_flow_state':
            # --- FIX: Actually clear the state when the command is processed. ---
            _clear_contact_flow_state(contact)
            logger.debug(f"Contact {contact.id}: Processed internal command to clear flow state.")
        elif action.get('type') == '_internal_command_switch_flow':
            logger.info(f"Contact {contact.id}: Processing final internal command to switch flow.")
            try:
                _clear_contact_flow_state(contact) # Clear old state before switching

                new_flow_name = action.get('target_flow_name')
                initial_context = action.get('initial_context', {})

                target_flow = Flow.objects.get(name=new_flow_name, is_active=True)
                entry_point_step = FlowStep.objects.filter(flow=target_flow, is_entry_point=True).first()

                if not entry_point_step:
                    raise ValueError(f"Flow '{new_flow_name}' is active but has no entry point step defined.")

                logger.info(f"Contact {contact.id}: Switching to flow '{target_flow.name}' at entry step '{entry_point_step.name}'.")
                
                # Create the new state
                new_contact_flow_state = ContactFlowState.objects.create(
                    contact=contact, current_flow=target_flow, current_step=entry_point_step,
                    flow_context_data=initial_context, started_at=timezone.now()
                )

                # Execute the new entry step's actions and add them to the final list
                entry_actions, updated_context = _execute_step_actions(entry_point_step, contact, initial_context.copy(), request=request)
                new_contact_flow_state.flow_context_data = updated_context
                new_contact_flow_state.save(update_fields=['flow_context_data', 'last_updated_at'])
                final_actions_for_meta_view.extend(entry_actions)
            except Exception as e:
                logger.error(f"Contact {contact.id}: Failed to process final switch flow command. Error: {e}", exc_info=True)
        elif action.get('type') == 'send_whatsapp_message': # Only pass valid message actions
            final_actions_for_meta_view.append(action)
        else:
            logger.warning(f"Unhandled action type in final processing: {action.get('type')}")
            
    return final_actions_for_meta_view
