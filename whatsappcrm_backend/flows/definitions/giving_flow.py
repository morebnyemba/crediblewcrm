# whatsappcrm_backend/flows/definitions/giving_flow.py

"""
A comprehensive giving flow that allows users to give online, view their
contribution history, and check the status of their last payment.
"""

GIVING_FLOW = {
    "name": "giving",
    "friendly_name": "Online Giving",
    "description": "Handles online and manual giving, viewing history, and checking status.",
    "trigger_keywords": ["give", "giving", "offering", "tithe", "start_giving"],
    "is_active": True,
    "steps": [
        {
        "name": "show_giving_options",
        "type": "question",
        "is_entry_point": True,
        "config": {
            "message_config": {
                "message_type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": "Welcome to the Giving section. What would you like to do?"},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": "give_online", "title": "Give Online"}},
                            {"type": "reply", "reply": {"id": "view_history", "title": "View Giving History"}},
                            {"type": "reply", "reply": {"id": "check_status", "title": "Check Payment Status"}}
                        ]
                    }
                }
            },
            "reply_config": {
                "expected_type": "interactive_id",
                "save_to_variable": "selected_giving_option"
            }
        },
        "transitions": [
            {
                "to_step": "ask_for_amount",
                "condition_config": {"type": "interactive_reply_id_equals", "value": "give_online"}
            },
            {
                "to_step": "query_payment_history",
                "condition_config": {"type": "interactive_reply_id_equals", "value": "view_history"}
            },
            {
                "to_step": "query_last_payment",
                "condition_config": {"type": "interactive_reply_id_equals", "value": "check_status"}
            }
        ]
    },

    # --- Path 1: Give Online ---
    {
        "name": "ask_for_amount",
        "type": "question",
        "config": {
            "message_config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you for your heart to give! ❤️\n\nHow much would you like to contribute today? Please enter a numeric amount (e.g., 10.50)."
                }
            },
            "reply_config": {
                "expected_type": "number",
                "validation_regex": "^(0(\\.\\d{1,2})?|[1-9]\\d*(\\.\\d{1,2})?)$",
                "save_to_variable": "giving_amount"
            },
            "fallback_config": {}
        },
        "transitions": [
            {
                "to_step": "ask_payment_type",
                "condition_config": {"type": "always_true"}
            }
        ]
    },
    {
        "name": "ask_payment_type",
        "type": "question",
        "config": {
            "message_config": {
                "message_type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": "Thank you! What is this contribution for?"},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": "tithe", "title": "Tithe"}},
                            {"type": "reply", "reply": {"id": "offering", "title": "Offering"}},
                            {"type": "reply", "reply": {"id": "pledge", "title": "Pledge"}}
                        ]
                    }
                }
            },
            "reply_config": {
                "expected_type": "interactive_id",
                "save_to_variable": "payment_type"
            }
        },
        "transitions": [
            {
                "to_step": "ask_payment_method",
                "condition_config": {"type": "always_true"}
            }
        ]
    },
    {
        "name": "ask_payment_method",
        "type": "question",
        "config": {
            "message_config": {
                "message_type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": "Payment Method"},
                    "body": {"text": "How would you like to give?"},
                    "action": {
                        "button": "Choose Method",
                        "sections": [{
                            "title": "Available Methods",
                            "rows": [
                                {"id": "ecocash", "title": "EcoCash"},
                                {"id": "manual_payment", "title": "Manual/Cash Payment"},
                                {"id": "omari", "title": "Omari", "description": "Coming Soon"},
                                {"id": "innbucks", "title": "Innbucks", "description": "Coming Soon"}
                            ]
                        }]
                    }
                }
            },
            "reply_config": {
                "expected_type": "interactive_id",
                "save_to_variable": "payment_method"
            }
        },
        "transitions": [
            {
                "to_step": "confirm_whatsapp_as_ecocash",
                "condition_config": {
                    "type": "interactive_reply_id_equals",
                    "value": "ecocash"
                }
            },
            {
                "to_step": "display_manual_payment_details",
                "condition_config": {
                    "type": "interactive_reply_id_equals",
                    "value": "manual_payment"
                }
            }
        ]
    },
    # --- EcoCash (Automated) Path ---
    {
        "name": "confirm_whatsapp_as_ecocash",
        "type": "question",
        "config": {
            "message_config": {
                "message_type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": "Is `{{ contact.whatsapp_id }}` the EcoCash number you'll be using?"},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": "yes_use_this_number", "title": "Yes, Use This Number"}},
                            {"type": "reply", "reply": {"id": "no_use_another", "title": "No, Use Another"}}
                        ]
                    }
                }
            },
            "reply_config": {
                "expected_type": "interactive_id",
                "save_to_variable": "confirm_ecocash_choice"
            }
        },
        "transitions": [
            {
                "to_step": "set_ecocash_from_contact",
                "condition_config": {"type": "interactive_reply_id_equals", "value": "yes_use_this_number"}
            },
            {
                "to_step": "ask_ecocash_phone_number",
                "condition_config": {"type": "interactive_reply_id_equals", "value": "no_use_another"}
            }
        ]
    },
    {
        "name": "set_ecocash_from_contact",
        "type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "set_context_variable",
                "variable_name": "ecocash_phone_number",
                # This template converts '2637...' to '07...'
                "value_template": "{{ '0' + contact.whatsapp_id[3:] if contact.whatsapp_id and contact.whatsapp_id.startswith('263') else contact.whatsapp_id }}"
            }]
        },
        "transitions": [{"to_step": "initiate_ecocash_payment", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "ask_ecocash_phone_number",
        "type": "question",
        "config": {
            "message_config": {
                "message_type": "text",
                "text": {"body": "Please enter the 10-digit EcoCash number you will be using to pay (e.g., 0772123456)."}
            },
            "reply_config": {
                "expected_type": "text",
                "save_to_variable": "ecocash_phone_number",
                "validation_regex": "^(07[78])\\d{7}$"
            },
            "fallback_config": {
                "action": "re_prompt",
                "max_retries": 2,
                "re_prompt_message_text": "That doesn't look like a valid Zimbabwean mobile number. Please enter a 10-digit number starting with 077 or 078.",
                "fallback_message_text": "Too many invalid attempts. Please type 'give' to restart."
            }
        },
        "transitions": [{"to_step": "initiate_ecocash_payment", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "initiate_ecocash_payment",
        "type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "initiate_paynow_giving_payment",
                "amount_template": "{{ giving_amount }}",
                "payment_type_template": "{{ payment_type }}",
                "payment_method_template": "{{ payment_method }}",
                "phone_number_template": "{{ ecocash_phone_number }}",
                "email_template": "{{ member_profile.email }}",
                "notes_template": "Online giving via WhatsApp flow."
            }]
        },
        "transitions": [
            {
                "to_step": "notify_admins_of_ecocash_initiation",
                "condition_config": {"type": "variable_equals", "variable_name": "paynow_initiation_success", "value": "True"}
            },
            {
                "to_step": "send_ecocash_failure_message",
                "condition_config": {"type": "always_true"}
            }
        ]
    },
    {
        "name": "notify_admins_of_ecocash_initiation",
        "type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "send_admin_notification",
                "message_template": "EcoCash payment of ${{ giving_amount }} ({{ payment_type|title }}) initiated by {{ contact.name or contact.whatsapp_id }}. Waiting for user to approve on their phone.",
                "notify_groups": ["Finance Team", "Pastoral Team"]
            }]
        },
        "transitions": [
            {"to_step": "send_ecocash_success_message", "condition_config": {"type": "always_true"}}
        ]
    },
    {
        "name": "send_ecocash_success_message",
        "type": "send_message",
        "config": {
            "message_type": "text",
            "text": {"body": "Thank you! Please check your phone and enter your EcoCash PIN to approve the payment of *${{ giving_amount }}*."}
        },
        "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "send_ecocash_failure_message",
        "type": "send_message",
        "config": {
            "message_type": "text",
            "text": {"body": "I'm sorry, there was a problem initiating the payment with Paynow. Please try again in a few moments.\n\n*Error:* {{ paynow_initiation_error }}"}
        },
        "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
    },

    # --- Manual Payment Path ---
    {
        "name": "display_manual_payment_details",
        "type": "send_message",
        "config": {
            "message_type": "text",
            "text": {
                "body": (
                    "Thank you for your heart to give! Please use one of the methods below:\n\n"
                    "🇺🇸 *International & USA*\n"
                    "1. *Bank of America*\n   - Routing: `061000052`\n   - Account: `3340 7458 7536`\n"
                    "2. *PayPal*\n   https://paypal.me/LifeInternational704\n"
                    "3. *Zelle*\n   `LifeInternationalusa@gmail.com`\n\n"
                    "🇿🇼 *Zimbabwe*\n"
                    "4. *EcoCash Merchant (USD/ZWG)*\n   Code: `030630`\n"
                    "5. *Agribank (ZWG)*\n   - Account: `100009498774`\n   - Branch: N. Mandela, Zimbabwe\n\n"
                    "After paying, please send a screenshot as proof of payment."
                )
            }
        },
        "transitions": [{"to_step": "ask_for_pop", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "ask_for_pop",
        "type": "question",
        "config": {
            "message_config": {
                "message_type": "text",
                "text": {"body": "Please send the image of your proof of payment now."}
            },
            "reply_config": {
                "expected_type": "image",
                "save_to_variable": "proof_of_payment_wamid"
            },
            "fallback_config": {
                "action": "re_prompt",
                "max_retries": 2,
                "re_prompt_message_text": "That doesn't seem to be an image. Please send a screenshot or photo of your proof of payment."
            }
        },
        "transitions": [{
            "to_step": "record_and_notify_manual_payment",
            "condition_config": {"type": "variable_exists", "variable_name": "proof_of_payment_wamid"}
        }]
    },
    {
        "name": "record_and_notify_manual_payment",
        "type": "action",
        "config": {
            "actions_to_run": [
                {
                    "action_type": "record_payment",
                    "amount_template": "{{ giving_amount }}",
                    "payment_type_template": "{{ payment_type }}",
                    "payment_method_template": "{{ payment_method }}",
                    "status_template": "pending_verification",
                    "notes_template": "Manual payment with proof submitted via WhatsApp.",
                    "proof_of_payment_wamid_template": "{{ proof_of_payment_wamid }}"
                },
                {
                    "action_type": "send_admin_notification",
                    "message_template": "Manual contribution of ${{ giving_amount }} ({{ payment_type|title }}) received from {{ contact.name or contact.whatsapp_id }}. Please verify the proof of payment in the CRM.",
                    "notify_groups": ["Finance Team", "Pastoral Team"]
                }
            ]
        },
        "transitions": [{"to_step": "send_manual_giving_confirmation", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "send_manual_giving_confirmation",
        "type": "send_message",
        "config": {
            "message_type": "text",
            "text": {"body": "Thank you for your generous gift! It has been submitted and is now pending verification by our team."}
        },
        "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
    },

    # --- Path 2: View History ---
    {
        "name": "query_payment_history",
        "type": "action",
        "config": {
            "actions_to_run": [
                {
                    "action_type": "query_model",
                    "app_label": "customer_data",
                    "model_name": "Payment",
                    "variable_name": "payment_history_list",
                    "filters_template": {"contact_id": "{{ contact.id }}"},
                    "order_by": ["-created_at"],
                    "limit": 5
                }
            ]
        },
        "transitions": [{"to_step": "check_if_history_exists", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "check_if_history_exists",
        "type": "action",
        "config": {"actions_to_run": []},
        "transitions": [
            {"to_step": "display_payment_history", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "payment_history_list.0"}},
            {"to_step": "no_payment_history_message", "priority": 20, "condition_config": {"type": "always_true"}}
        ]
    },
    {
        "name": "display_payment_history",
        "type": "send_message",
        "config": {
            "message_type": "text",
            "text": {
                "body": (
                    "Here are your last {{ payment_history_list|length }} contributions:\n\n"
                    "{% for payment in payment_history_list %}"
                    "🗓️ *{{ payment.created_at|strftime('%b %d, %Y') }}:* {{ payment.currency }} {{ payment.amount }} ({{ payment.payment_type|title }})\n"
                    "Status: *{{ payment.status|replace('_', ' ')|title }}*\n"
                    "{% if not loop.last %}---\n{% endif %}"
                    "{% endfor %}"
                )
            }
        },
        "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "no_payment_history_message",
        "type": "send_message",
        "config": {
            "message_type": "text",
            "text": {"body": "You do not have any giving history with us yet. We look forward to your first contribution!"}
        },
        "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
    },

    # --- Path 3: Check Status ---
    {
        "name": "query_last_payment",
        "type": "action",
        "config": {
            "actions_to_run": [
                {
                    "action_type": "query_model",
                    "app_label": "customer_data",
                    "model_name": "Payment",
                    "variable_name": "last_payment_list",
                    "filters_template": {"contact_id": "{{ contact.id }}"},
                    "order_by": ["-created_at"],
                    "limit": 1
                }
            ]
        },
        "transitions": [{"to_step": "check_if_last_payment_exists", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "check_if_last_payment_exists",
        "type": "action",
        "config": {"actions_to_run": []},
        "transitions": [
            {"to_step": "set_last_payment_variable", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "last_payment_list.0"}},
            {"to_step": "no_payment_history_message", "priority": 20, "condition_config": {"type": "always_true"}}
        ]
    },
    {
        "name": "set_last_payment_variable",
        "type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "set_context_variable",
                "variable_name": "last_payment",
                "value_template": "{{ last_payment_list[0] }}"
            }]
        },
        "transitions": [{"to_step": "display_last_payment_status", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "display_last_payment_status",
        "type": "send_message",
        "config": {
            "message_type": "text",
            "text": {
                "body": (
                    "Here is the status of your most recent contribution:\n\n"
                    "🗓️ *{{ last_payment.created_at|strftime('%b %d, %Y') }}:* {{ last_payment.currency }} {{ last_payment.amount }} ({{ last_payment.payment_type|title }})\n"
                    "Status: *{{ last_payment.status|replace('_', ' ')|title }}*"
                )
            }
        },
        "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
    },

    # --- Shared End/Loop Steps ---
    {
        "name": "offer_return_to_menu",
        "type": "question",
        "config": {
            "message_config": {
                "message_type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": "Is there anything else I can help you with in the giving section?"},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": "giving_menu", "title": "Giving Menu"}},
                            {"type": "reply", "reply": {"id": "main_menu", "title": "Main Menu"}}
                        ]
                    }
                }
            },
            "reply_config": {"save_to_variable": "final_choice", "expected_type": "interactive_id"}
        },
        "transitions": [
            {"to_step": "show_giving_options", "condition_config": {"type": "interactive_reply_id_equals", "value": "giving_menu"}},
            {"to_step": "switch_to_main_menu", "condition_config": {"type": "interactive_reply_id_equals", "value": "main_menu"}}
        ]
    },
    {
        "name": "switch_to_main_menu",
        "type": "switch_flow",
        "config": {"target_flow_name": "main_menu"},
        "transitions": []
    }
    ]
}
