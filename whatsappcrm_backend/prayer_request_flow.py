# whatsappcrm_backend/flows/definitions/prayer_request_flow.py

"""
This flow definition guides a user through submitting a prayer request,
including the request details, category, and anonymity preference.
"""

PRAYER_REQUEST_FLOW = {
    "name": "prayer_request",
    "friendly_name": "Submit Prayer Request",
    "description": "Guides a user through submitting a prayer request.",
    "trigger_keywords": ["prayer", "pray for me", "prayer request"],
    "is_active": True,
    "steps": [
        # 1. Ask for the prayer request text
        {
            "name": "ask_for_request",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "We are honored to pray for you. Please share your prayer request with us."
                    }
                },
                "reply_config": {
                    "save_to_variable": "prayer_request_text",
                    "expected_type": "text"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 1,
                    "re_prompt_message_text": "Please type out your prayer request so we can pray for you.",
                    "fallback_message_text": "Sorry, I didn't understand. Please type 'prayer' to start again."
                }
            },
            "transitions": [
                {"to_step": "ask_for_category", "condition_config": {"type": "always_true"}}
            ]
        },
        # 2. Ask for category
        {
            "name": "ask_for_category",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {"type": "text", "text": "Prayer Category"},
                        "body": {"text": "To help us pray more specifically, please choose a category for your request."},
                        "action": {
                            "button": "Choose Category",
                            "sections": [{
                                "title": "Categories",
                                "rows": [
                                    {"id": "healing", "title": "Healing"},
                                    {"id": "family", "title": "Family & Relationships"},
                                    {"id": "guidance", "title": "Guidance & Wisdom"},
                                    {"id": "thanksgiving", "title": "Thanksgiving"},
                                    {"id": "financial", "title": "Financial Provision"},
                                    {"id": "other", "title": "Other"}
                                ]
                            }]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "prayer_category",
                    "expected_type": "interactive_id"
                }
            },
            "transitions": [
                {"to_step": "ask_anonymity", "condition_config": {"type": "always_true"}}
            ]
        },
        # 3. Ask about anonymity
        {
            "name": "ask_anonymity",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "Would you like this prayer request to be anonymous? Your name will not be shared with the prayer team."},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "anonymous_yes", "title": "Yes, keep it anonymous"}},
                                {"type": "reply", "reply": {"id": "anonymous_no", "title": "No, use my name"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "anonymity_choice",
                    "expected_type": "interactive_id"
                }
            },
            "transitions": [
                {"to_step": "set_anonymity_true", "condition_config": {"type": "interactive_reply_id_equals", "value": "anonymous_yes"}},
                {"to_step": "set_anonymity_false", "condition_config": {"type": "interactive_reply_id_equals", "value": "anonymous_no"}}
            ]
        },
        # 4a. Set anonymity to True
        {
            "name": "set_anonymity_true",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "set_context_variable", "variable_name": "is_anonymous", "value_template": True}]},
            "transitions": [{"to_step": "record_prayer_request_action", "condition_config": {"type": "always_true"}}]
        },
        # 4b. Set anonymity to False
        {
            "name": "set_anonymity_false",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "set_context_variable", "variable_name": "is_anonymous", "value_template": False}]},
            "transitions": [{"to_step": "record_prayer_request_action", "condition_config": {"type": "always_true"}}]
        },
        # 5. Record the prayer request
        {
            "name": "record_prayer_request_action",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "record_prayer_request",
                    "request_text_template": "{{ context.prayer_request_text }}",
                    "category_template": "{{ context.prayer_category }}",
                    "is_anonymous_template": "{{ context.is_anonymous }}"
                }]
            },
            "transitions": [{"to_step": "end_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 6. End the flow with a confirmation
        {
            "name": "end_prayer_request",
            "type": "end_flow",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Thank you for trusting us with your prayer request. Our prayer team will be lifting you up. Be blessed. 🙏"}
                }
            },
            "transitions": []
        }
    ]
}