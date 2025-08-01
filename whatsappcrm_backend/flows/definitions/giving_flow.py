# whatsappcrm_backend/flows/definitions/giving_flow.py

"""
This flow definition handles the process of online giving, allowing users
to specify an amount, type of giving, and payment method.
"""

GIVING_FLOW = {
    "name": "giving",
    "friendly_name": "Online Giving",
    "description": "Guides a user through making a tithe or offering.",
    "trigger_keywords": ["give", "offering", "tithe", "donate"],
    "is_active": True,
    "steps": [
        # 1. Ask for the amount
        {
            "name": "ask_for_amount",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Thank you for your heart to give! ❤️\n\nHow much would you like to contribute today? Please enter a numeric amount (e.g., 10.50)."
                    }
                },
                "reply_config": {
                    "save_to_variable": "giving_amount",
                    "expected_type": "number"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Sorry, that doesn't look like a valid amount. Please enter a number (e.g., 10 or 25.50).",
                    "fallback_message_text": "Sorry, we couldn't process that. Please type 'give' to try again."
                }
            },
            "transitions": [
                {"to_step": "ask_payment_type", "condition_config": {"type": "always_true"}}
            ]
        },

        # 2. Ask for the type of payment (Tithe, Offering, etc.)
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
                    "save_to_variable": "payment_type",
                    "expected_type": "interactive_id"
                }
            },
            "transitions": [
                {"to_step": "ask_payment_method", "condition_config": {"type": "always_true"}}
            ]
        },

        # 3. Ask for the payment method
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
                    "save_to_variable": "payment_method",
                    "expected_type": "interactive_id"
                }
            },
            "transitions": [
                {"to_step": "ask_ecocash_phone_number", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "ecocash"}},
                {"to_step": "ask_for_transaction_ref", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "manual_payment"}},
                {"to_step": "handle_coming_soon", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },

        # 4a. Ask for EcoCash phone number
        {
            "name": "ask_ecocash_phone_number",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Please enter the EcoCash number you will be using to pay (e.g., 0772123456)."
                    }
                },
                "reply_config": {
                    "save_to_variable": "ecocash_phone_number",
                    "expected_type": "text",
                    "validation_regex": "^(07[78])\\d{7}$"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "That doesn't look like a valid Zimbabwean mobile number. Please enter a 10-digit number starting with 077 or 078.",
                    "fallback_message_text": "Sorry, we couldn't process that. Please type 'give' to try again."
                }
            },
            "transitions": [
                {"to_step": "initiate_ecocash_payment", "condition_config": {"type": "always_true"}}
            ]
        },

        # 4b. Initiate the Paynow transaction for EcoCash
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
                    "currency_template": "USD",
                    "notes_template": "Online giving via WhatsApp flow."
                }]
            },
            "transitions": [
                {"to_step": "send_ecocash_prompt_message", "priority": 10, "condition_config": {"type": "variable_equals", "variable_name": "paynow_initiation_success", "value": "True"}},
                {"to_step": "send_ecocash_failure_message", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },

        # 4c. Inform user of success and next steps
        {
            "name": "send_ecocash_prompt_message",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you! I've initiated the payment. Please check your phone and enter your EcoCash PIN to approve the transaction of ${{ giving_amount }}.\n\nWe will send you a confirmation message once the payment is complete."
                }
            },
            "transitions": [{"to_step": "end_giving", "condition_config": {"type": "always_true"}}]
        },

        # 4d. Inform user of failure
        {
            "name": "send_ecocash_failure_message",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "I'm sorry, there was a problem initiating the payment with Paynow. Please try again in a few moments.\n\nError: {{ paynow_initiation_error }}"
                }
            },
            "transitions": [{"to_step": "ask_payment_method", "condition_config": {"type": "always_true"}}]
        },

        # 5a. Ask for transaction reference for manual payments
        {
            "name": "ask_for_transaction_ref",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "You've selected a manual payment. Please enter the transaction ID or receipt number for your contribution."}
                },
                "reply_config": {"save_to_variable": "transaction_ref", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Sorry, I didn't get that. Please enter the transaction reference number.", "fallback_message_text": "Sorry, we couldn't process that. Please type 'give' to try again."}
            },
            "transitions": [{"to_step": "record_manual_payment_action", "condition_config": {"type": "always_true"}}]
        },

        # 5b. Handle methods that are not ready yet
        {
            "name": "handle_coming_soon",
            "type": "send_message", "config": {"message_type": "text", "text": {"body": "The payment method '{{ payment_method }}' is coming soon! Please select another method for now."}},
            "transitions": [{"to_step": "ask_payment_method", "condition_config": {"type": "always_true"}}]
        },

        # 6a. Record the manual payment using an action
        {
            "name": "record_manual_payment_action",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "record_payment",
                    "amount_template": "{{ giving_amount }}",
                    "payment_type_template": "{{ payment_type }}",
                    "payment_method_template": "{{ payment_method }}",
                    "transaction_ref_template": "{{ transaction_ref|default:'' }}",
                    "currency_template": "USD",
                    "notes_template": "Online giving via WhatsApp flow (Manual).",
                    "status_template": "completed"
                }]
            },
            "transitions": [{"to_step": "end_giving_manual_confirmation", "condition_config": {"type": "always_true"}}]
        },

        # 6b. Confirmation for manual payment
        {
            "name": "end_giving_manual_confirmation",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Thank you for your contribution! We have recorded your manual payment with reference '{{ transaction_ref }}'. It will be verified by our finance team."
                }
            },
            "transitions": [{"to_step": "end_giving", "condition_config": {"type": "always_true"}}]
        },

        # 7. End the flow
        {
            "name": "end_giving",
            "type": "end_flow",
            "config": {},
            "transitions": []
        }
    ]
}