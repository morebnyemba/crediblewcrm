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
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Sorry, that's not a valid selection. Please choose one of the buttons.",
                    "fallback_message_text": "If you need help, just type 'menu' to see the options again."
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
            "transitions": [{"to_step": "confirm_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 4b. Set anonymity to False
        {
            "name": "set_anonymity_false",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "set_context_variable", "variable_name": "is_anonymous", "value_template": False}]},
            "transitions": [{"to_step": "confirm_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 5. Ask user to confirm details before submitting
        {
            "name": "confirm_prayer_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "Confirm Your Request"},
                        "body": {
                            "text": "Please review your prayer request:\n\n*Category:* {{ context.prayer_category|title }}\n*Anonymous:* {{ context.is_anonymous }}\n\n*Request:*\n\"{{ context.prayer_request_text }}\"\n\nDoes this look correct?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_submit", "title": "Yes, Submit"}},
                                {"type": "reply", "reply": {"id": "restart_request", "title": "No, Start Over"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "confirmation_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "record_prayer_request_action", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_submit"}},
                {"to_step": "ask_for_request", "condition_config": {"type": "interactive_reply_id_equals", "value": "restart_request"}}
            ]
        },
        # 6. Record the prayer request after confirmation
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
            "transitions": [{"to_step": "notify_admin_of_request", "condition_config": {"type": "always_true"}}]
        },
        # 7. Notify Admin
        {
            "name": "notify_admin_of_request",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "send_admin_notification",
                    "message_template": "New Prayer Request Received:\n\nFrom: {{ contact.name }} ({{ contact.whatsapp_id }})\nAnonymous: {{ context.is_anonymous }}\nCategory: {{ context.prayer_category }}\n\nRequest:\n\"{{ context.prayer_request_text }}\""
                }]
            },
            "transitions": [{"to_step": "end_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 8. End the flow with a confirmation and offer next steps
        {
            "name": "end_prayer_request",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "Thank you for trusting us with your prayer request. Our prayer team will be lifting you up. Be blessed. 🙏\n\nIs there anything else I can help you with?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "return_to_menu", "title": "Main Menu"}},
                                {"type": "reply", "reply": {"id": "end_conversation", "title": "No, I'm Done"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "final_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "switch_to_main_menu", "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}},
                {"to_step": "end_flow_goodbye", "condition_config": {"type": "interactive_reply_id_equals", "value": "end_conversation"}}
            ]
        },
        # 9a. Switch back to the main menu
        {
            "name": "switch_to_main_menu",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "switch_flow", "target_flow_name": "main_menu"}]},
            "transitions": []
        },
        # 9b. End the flow with a simple goodbye
        {
            "name": "end_flow_goodbye",
            "type": "end_flow",
            "config": {"message_config": {"message_type": "text", "text": {"body": "You're welcome! Have a blessed day."}}},
            "transitions": []
        }
    ]
}