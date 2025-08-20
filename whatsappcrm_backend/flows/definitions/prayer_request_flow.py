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
        # 1. Ask for membership status
        {
            "name": "ask_membership_status",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "Welcome! To help us direct your prayer request, could you please let us know if you are a registered member of our church?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "member_yes", "title": "Yes, I am"}},
                                {"type": "reply", "reply": {"id": "member_no", "title": "No, I'm not"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "membership_choice",
                    "expected_type": "interactive_id"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 1,
                    "re_prompt_message_text": "Please tap one of the buttons to let us know if you're a member."
                }
            },
            "transitions": [
                {"to_step": "set_member_status_true", "condition_config": {"type": "interactive_reply_id_equals", "value": "member_yes"}},
                {"to_step": "set_member_status_false", "condition_config": {"type": "interactive_reply_id_equals", "value": "member_no"}}
            ]
        },
        # 2a. Set member status to True
        {
            "name": "set_member_status_true",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "set_context_variable", "variable_name": "submitted_as_member", "value_template": True}]},
            "transitions": [{"to_step": "ask_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 2b. Set member status to False
        {
            "name": "set_member_status_false",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "set_context_variable", "variable_name": "submitted_as_member", "value_template": False}]},
            "transitions": [{"to_step": "ask_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 3. Ask for the prayer request text (was step 1)
        {
            "name": "ask_prayer_request",
            "is_entry_point": False,
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
            "transitions": [{"to_step": "ask_category", "condition_config": {"type": "always_true"}}]
        },
        # 4. Ask for category (was step 2)
        {

            "name": "ask_category",
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
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Please make a selection from the list to continue."
                }
            },
            "transitions": [
                {"to_step": "ask_anonymity", "condition_config": {"type": "always_true"}}
            ]
        },
        # 5. Ask about anonymity (was step 3)
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
                                {"type": "reply", "reply": {"id": "anonymous_yes", "title": "Yes, Anonymous"}},
                                {"type": "reply", "reply": {"id": "anonymous_no", "title": "No, Use My Name"}}
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
        # 6a. Set anonymity to True (was step 4a)
        {

            "name": "set_anonymity_true",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "set_context_variable", "variable_name": "is_anonymous", "value_template": True}]},
            "transitions": [{"to_step": "confirm_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 6b. Set anonymity to False (was step 4b)
        {

            "name": "set_anonymity_false",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "set_context_variable", "variable_name": "is_anonymous", "value_template": False}]},
            "transitions": [{"to_step": "confirm_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 7. Ask user to confirm details before submitting (was step 5)
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
                            "text": "Please review your prayer request:\n\n*Category:* {{ prayer_category|title }}\n*Anonymous:* {{ is_anonymous }}\n\n*Request:*\n\"{{ prayer_request_text }}\"\n\nDoes this look correct?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_submit", "title": "Yes, Submit"}},
                                {"type": "reply", "reply": {"id": "restart_request", "title": "No, Start Over"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "confirmation_choice", "expected_type": "interactive_id"},
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 1,
                    "re_prompt_message_text": "Please tap one of the buttons to confirm."
                }
            },
            "transitions": [
                {"to_step": "record_prayer_request_action", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_submit"}},

                {"to_step": "ask_prayer_request", "condition_config": {"type": "interactive_reply_id_equals", "value": "restart_request"}}
            ]
        },
        # 8. Record the prayer request after confirmation (was step 6)
        {

            "name": "record_prayer_request_action",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "record_prayer_request",
                    "request_text_template": "{{ prayer_request_text }}",
                    "category_template": "{{ prayer_category }}",
                    "is_anonymous_template": "{{ is_anonymous }}",
                    "submitted_as_member_template": "{{ submitted_as_member }}"
                }]
            },
            "transitions": [{"to_step": "notify_admin_of_request", "condition_config": {"type": "always_true"}}]
        },
        # 9. Notify Admin (was step 7)
        {

            "name": "notify_admin_of_request",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "send_admin_notification",
                    "notify_groups": ["Admins", "Prayer Team"],
                    "message_template": "New Prayer Request Received:\n\nFrom: {{ contact.name }} ({{ contact.whatsapp_id }})\nAnonymous: {{ is_anonymous }}\nCategory: {{ prayer_category|title }}\n\nRequest:\n\"{{ prayer_request_text }}\""
                }]
            },
            "transitions": [{"to_step": "end_prayer_request", "condition_config": {"type": "always_true"}}]
        },
        # 10. End the flow with a confirmation and offer next steps (was step 8)
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
                "reply_config": {"save_to_variable": "final_choice", "expected_type": "interactive_id"},
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 1,
                    "re_prompt_message_text": "Please choose one of the options to continue."
                }
            },
            "transitions": [
                {"to_step": "switch_to_main_menu", "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}},
                {"to_step": "end_flow_goodbye", "condition_config": {"type": "interactive_reply_id_equals", "value": "end_conversation"}}
            ]
        },
        # 11a. Switch back to the main menu (was step 9a)
        {
            "name": "switch_to_main_menu",
            "type": "switch_flow",
            "config": {"target_flow_name": "main_menu"},
            "transitions": []
        },
        # 11b. End the flow with a simple goodbye (was step 9b)
        {
            "name": "end_flow_goodbye",
            "type": "end_flow",
            "config": {"message_config": {"message_type": "text", "text": {"body": "You're welcome! Have a blessed day."}}},
            "transitions": []
        }
    ]
}