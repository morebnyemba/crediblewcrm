# whatsappcrm_backend/flows/definitions/giving_flow.py

# A more robust and user-friendly giving flow.
# - Handles automated Paynow payments for EcoCash.
# - Handles manual payments with image proof of payment.
# - Asks to reuse the contact's number for EcoCash to save typing.

giving_flow_steps = [
    {
        "name": "ask_for_amount",
        "step_type": "question",
        "is_entry_point": True,
        "config": {
            "message_config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you for your heart to give! ❤️\n\nHow much would you like to contribute today? Please enter a numeric amount (e.g., 10.50)."
                }
            },
            "reply_config": {
                "expected_type": "number",
                "validation_regex": "^\\d+(\\.\\d{1,2})?$",
                "save_to_variable": "giving_amount"
            },
            "fallback_config": {
                "action": "re_prompt",
                "max_retries": 2,
                "re_prompt_message_text": "Sorry, that doesn't look like a valid amount. Please enter a number (e.g., 10 or 25.50).",
                "fallback_message_text": "Sorry, we couldn't process that. Please type 'give' to try again."
            }
        },
        "transitions": [
            {
                "next_step": "ask_payment_type",
                "condition_config": {"type": "always_true"}
            }
        ]
    },
    {
        "name": "ask_payment_type",
        "step_type": "question",
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
                "next_step": "ask_payment_method",
                "condition_config": {"type": "always_true"}
            }
        ]
    },
    {
        "name": "ask_payment_method",
        "step_type": "question",
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
                "next_step": "confirm_whatsapp_as_ecocash",
                "condition_config": {
                    "type": "interactive_reply_id_equals",
                    "value": "ecocash"
                }
            },
            {
                "next_step": "display_manual_payment_details",
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
        "step_type": "question",
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
                "next_step": "set_ecocash_from_contact",
                "condition_config": {"type": "interactive_reply_id_equals", "value": "yes_use_this_number"}
            },
            {
                "next_step": "ask_ecocash_phone_number",
                "condition_config": {"type": "interactive_reply_id_equals", "value": "no_use_another"}
            }
        ]
    },
    {
        "name": "set_ecocash_from_contact",
        "step_type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "set_context_variable",
                "variable_name": "ecocash_phone_number",
                "value_template": "{{ contact.whatsapp_id }}"
            }]
        },
        "transitions": [{"next_step": "validate_ecocash_number", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "ask_ecocash_phone_number",
        "step_type": "question",
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
        "transitions": [{"next_step": "validate_ecocash_number", "condition_config": {"type": "always_true"}}]
    },
        {
        "name": "validate_ecocash_number",
        "step_type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "validate_phone_number",
                "variable_name": "ecocash_phone_number",
                "country_code": "ZW"
            }]
        },
        "transitions": [
            {
                "next_step": "initiate_ecocash_payment",
                "condition_config": {"type": "variable_equals", "variable_name": "is_valid_number", "value": "True"}
            },
            {
                "next_step": "send_invalid_number_message",
                "condition_config": {"type": "variable_equals", "variable_name": "is_valid_number", "value": "False"}
            }
        ]
    },
    {
        "name": "initiate_ecocash_payment",
        "step_type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "initiate_paynow_giving_payment",
                "amount_template": "{{ giving_amount }}",
                "payment_type_template": "{{ payment_type }}",
                "payment_method_template": "{{ payment_method }}",
                "phone_number_template": "{{ ecocash_phone_number }}",
                "email_template": "{{ member_profile.email }}",
                "currency_template": "USD",
                "notes_template": "Online giving via WhatsApp flow."
            }]
        },
        "transitions": [
            {
                "next_step": "send_ecocash_success_message",
                "condition_config": {"type": "variable_equals", "variable_name": "paynow_initiation_success", "value": "True"}
            },
            {
                "next_step": "send_payment_failure_message",
                "condition_config": {"type": "always_true"}
            }
        ]
    },
    {
        "name": "send_ecocash_success_message",
        "step_type": "send_message",
        "config": {
             "message_config": {
                "message_type": "text",
                "text": {"body": "Thank you! Please check your phone and enter your EcoCash PIN to approve the payment of *${{ giving_amount }}*."}
            }
        }
    },
    {
        "name": "send_invalid_number_message",
        "step_type": "send_message",
        "config": {
            "message_type": "text",
            "text": {"body": "Sorry, that's not a valid Zimbabwean number. Please enter a 10-digit number starting with 077 or 078."}
        },
        "transitions": [{"next_step": "ask_payment_method", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "send_payment_failure_message",
        "step_type": "send_message",
        "config": {
            "message_type": "text",
            "text": {"body": "I'm sorry, there was a problem initiating the payment with Paynow. Please try again in a few moments.\n\n*Error:* {{ paynow_initiation_error }}"}
        },

        "transitions": [{"next_step": "ask_payment_method", "condition_config": {"type": "always_true"}}]
    },

    # --- Manual Payment Path ---
    {
        "name": "display_manual_payment_details",
        "step_type": "send_message",
        "config": {
            "message_type": "text",
            "text": {
                "body": (
                    "Thank you. Please use one of the methods below to give:\n\n"
                    "🏦 *Bank Transfer*\n"
                    "Bank: Steward Bank\n"
                    "Account: 123456789\n\n"
                    "📱 *Merchant Code*\n"
                    "Code: *123*456*1#\n\n"
                    "After paying, please send a screenshot as proof of payment."
                )
            }
        },
        "transitions": [{"next_step": "ask_for_pop", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "ask_for_pop",
        "step_type": "question",
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
            "next_step": "record_manual_payment",
            "condition_config": {"type": "variable_exists", "variable_name": "proof_of_payment_wamid"}
        }]
    },
    {
        "name": "record_manual_payment",
        "step_type": "action",
        "config": {
            "actions_to_run": [{
                "action_type": "record_payment",
                "amount_template": "{{ giving_amount }}",
                "payment_type_template": "{{ payment_type }}",
                "payment_method_template": "manual_payment",
                "status_template": "pending_verification",
                "notes_template": "Manual payment with proof submitted via WhatsApp.",
                "proof_of_payment_wamid_template": "{{ proof_of_payment_wamid }}"
            }]
        },
        "transitions": [{"next_step": "end_flow_after_manual", "condition_config": {"type": "always_true"}}]
    },
    {
        "name": "end_flow_after_manual",
        "step_type": "end_flow",
        "config": {}
    }
]
