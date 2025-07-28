# whatsappcrm_backend/flows/schemas.py

import logging
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, field_validator, model_validator, Field

logger = logging.getLogger(__name__)

try:
    from media_manager.models import MediaAsset # For asset_pk lookup
    MEDIA_ASSET_ENABLED = True
except ImportError:
    MEDIA_ASSET_ENABLED = False
    logger.warning("MediaAsset model not found or could not be imported. MediaAsset functionality (e.g., 'asset_pk') will be disabled in flows.")


class BasePydanticConfig(BaseModel):
    class Config:
        extra = 'forbid'

# --- Configs for 'send_message' step ---
class TextMessageContent(BasePydanticConfig):
    body: str = Field(..., min_length=1, max_length=4096)
    preview_url: bool = False

class MediaMessageContent(BasePydanticConfig):
    asset_pk: Optional[int] = None
    id: Optional[str] = None
    link: Optional[str] = None
    caption: Optional[str] = Field(default=None, max_length=1024)
    filename: Optional[str] = None

    @model_validator(mode='after')
    def check_media_source(self):
        if not MEDIA_ASSET_ENABLED and self.asset_pk:
             raise ValueError("'asset_pk' provided but MediaAsset system is not enabled/imported.")
        if not (self.asset_pk or self.id or self.link):
            raise ValueError("One of 'asset_pk', 'id', or 'link' must be provided for media.")
        return self

class MediaHeaderContent(BasePydanticConfig):
    id: Optional[str] = None
    link: Optional[str] = None

    @model_validator(mode='after')
    def check_media_source(self):
        if not (self.id or self.link):
            raise ValueError("One of 'id' or 'link' must be provided for a media header.")
        return self

class InteractiveButtonReply(BasePydanticConfig):
    id: str = Field(..., min_length=1, max_length=256)
    title: str = Field(..., min_length=1, max_length=20)

class InteractiveButton(BasePydanticConfig):
    type: Literal["reply"] = "reply"
    reply: InteractiveButtonReply

class InteractiveButtonAction(BasePydanticConfig):
    buttons: List[InteractiveButton] = Field(..., min_items=1, max_items=3)

class InteractiveHeader(BasePydanticConfig):
    type: Literal["text", "video", "image", "document"]
    text: Optional[str] = Field(default=None, max_length=60)
    image: Optional[MediaHeaderContent] = None
    video: Optional[MediaHeaderContent] = None
    document: Optional[MediaHeaderContent] = None

    @model_validator(mode='after')
    def check_content_matches_type(self):
        type_to_field = {'text': 'text', 'image': 'image', 'video': 'video', 'document': 'document'}
        field_name = type_to_field.get(self.type)
        if not field_name or getattr(self, field_name) is None:
            raise ValueError(f"For header type '{self.type}', the '{field_name}' field must be provided.")
        for t, f in type_to_field.items():
            if t != self.type and getattr(self, f) is not None:
                raise ValueError(f"For header type '{self.type}', only the '{field_name}' field should be provided, not '{f}'.")
        return self

class InteractiveBody(BasePydanticConfig):
    text: str = Field(..., min_length=1, max_length=1024)

class InteractiveFooter(BasePydanticConfig):
    text: str = Field(..., min_length=1, max_length=60)

class InteractiveListRow(BasePydanticConfig):
    id: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=24)
    description: Optional[str] = Field(default=None, max_length=72)

class InteractiveListSection(BasePydanticConfig):
    title: Optional[str] = Field(default=None, max_length=24)
    rows: List[InteractiveListRow] = Field(..., min_items=1, max_items=10)

class InteractiveListAction(BasePydanticConfig):
    button: str = Field(..., min_length=1, max_length=20)
    sections: List[InteractiveListSection] = Field(..., min_items=1)

class InteractiveMessagePayload(BasePydanticConfig):
    type: Literal["button", "list", "product", "product_list"]
    header: Optional[InteractiveHeader] = None
    body: InteractiveBody
    footer: Optional[InteractiveFooter] = None
    action: Union[InteractiveButtonAction, InteractiveListAction]

class TemplateLanguage(BasePydanticConfig):
    code: str

class TemplateParameter(BasePydanticConfig):
    type: Literal["text", "currency", "date_time", "image", "document", "video", "payload"]
    text: Optional[str] = None
    currency: Optional[Dict[str, Any]] = None
    date_time: Optional[Dict[str, Any]] = None
    image: Optional[Dict[str, Any]] = None
    document: Optional[Dict[str, Any]] = None
    video: Optional[Dict[str, Any]] = None
    payload: Optional[str] = None

class TemplateComponent(BasePydanticConfig):
    type: Literal["header", "body", "button"]
    sub_type: Optional[Literal['url', 'quick_reply', 'call_button', 'catalog_button', 'mpm_button']] = None
    parameters: Optional[List[TemplateParameter]] = None
    index: Optional[int] = None

class TemplateMessageContent(BasePydanticConfig):
    name: str
    language: TemplateLanguage
    components: Optional[List[TemplateComponent]] = None

class ContactName(BasePydanticConfig):
    formatted_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    suffix: Optional[str] = None
    prefix: Optional[str] = None

class ContactAddress(BasePydanticConfig):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    type: Optional[Literal['HOME', 'WORK']] = None

class ContactEmail(BasePydanticConfig):
    email: Optional[str] = None
    type: Optional[Literal['HOME', 'WORK']] = None

class ContactPhone(BasePydanticConfig):
    phone: Optional[str] = None
    type: Optional[Literal['CELL', 'MAIN', 'IPHONE', 'HOME', 'WORK']] = None
    wa_id: Optional[str] = None

class ContactOrg(BasePydanticConfig):
    company: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None

class ContactUrl(BasePydanticConfig):
    url: Optional[str] = None
    type: Optional[Literal['HOME', 'WORK']] = None

class ContactObject(BasePydanticConfig):
    addresses: Optional[List[ContactAddress]] = None
    birthday: Optional[str] = None
    emails: Optional[List[ContactEmail]] = None
    name: ContactName
    org: Optional[ContactOrg] = None
    phones: Optional[List[ContactPhone]] = None
    urls: Optional[List[ContactUrl]] = None

class LocationMessageContent(BasePydanticConfig):
    longitude: float
    latitude: float
    name: Optional[str] = None
    address: Optional[str] = None

class StepConfigSendMessage(BasePydanticConfig):
    message_type: Literal["text", "image", "document", "audio", "video", "sticker", "interactive", "template", "contacts", "location"]
    text: Optional[TextMessageContent] = None
    image: Optional[MediaMessageContent] = None
    document: Optional[MediaMessageContent] = None
    audio: Optional[MediaMessageContent] = None
    video: Optional[MediaMessageContent] = None
    sticker: Optional[MediaMessageContent] = None
    interactive: Optional[InteractiveMessagePayload] = None
    template: Optional[TemplateMessageContent] = None
    contacts: Optional[List[ContactObject]] = None
    location: Optional[LocationMessageContent] = None

    @model_validator(mode='after')
    def check_payload_exists_for_type(self):
        msg_type = self.message_type
        payload_specific_to_type = getattr(self, msg_type, None)
        if payload_specific_to_type is None:
            raise ValueError(f"Payload for message_type '{msg_type}' is missing or null.")
        if msg_type == 'interactive' and self.interactive:
            if not self.interactive.type:
                raise ValueError("For 'interactive' messages, the 'interactive' payload must exist and specify its own 'type' (e.g., 'button', 'list').")
        return self

class ReplyConfig(BasePydanticConfig):
    save_to_variable: str
    expected_type: Literal["text", "email", "number", "interactive_id"]
    validation_regex: Optional[str] = None

class StepConfigQuestion(BasePydanticConfig):
    message_config: StepConfigSendMessage
    reply_config: ReplyConfig

class ActionItemConfig(BasePydanticConfig):
    action_type: Literal["set_context_variable", "update_contact_field", "update_member_profile", "switch_flow"]
    variable_name: Optional[str] = None
    value_template: Optional[Any] = None
    field_path: Optional[str] = None
    fields_to_update: Optional[Dict[str, Any]] = None
    target_flow_name: Optional[str] = None
    initial_context_template: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode='after')
    def check_action_fields(self):
        action_type = self.action_type
        if action_type == 'set_context_variable':
            if self.variable_name is None or self.value_template is None:
                raise ValueError("For set_context_variable, 'variable_name' and 'value_template' are required.")
        elif action_type == 'update_contact_field':
            if not self.field_path or self.value_template is None:
                raise ValueError("For update_contact_field, 'field_path' and 'value_template' are required.")
        elif action_type == 'update_member_profile':
            if not self.fields_to_update or not isinstance(self.fields_to_update, dict):
                raise ValueError("For update_member_profile, 'fields_to_update' (a dictionary) is required.")
        elif action_type == 'switch_flow':
            if not self.target_flow_name:
                raise ValueError("For switch_flow, 'target_flow_name' is required.")
        return self

class StepConfigAction(BasePydanticConfig):
    actions_to_run: List[ActionItemConfig] = Field(default_factory=list)

class StepConfigHumanHandover(BasePydanticConfig):
    pre_handover_message_text: Optional[str] = None
    notification_details: Optional[str] = None

class StepConfigEndFlow(BasePydanticConfig):
    message_config: Optional[StepConfigSendMessage] = None

# Rebuild InteractiveMessagePayload if it had forward references to models defined after it
InteractiveMessagePayload.model_rebuild()