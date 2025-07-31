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
                {"to_step": "record_payment_action", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "ecocash"}},
                {"to_step": "ask_for_transaction_ref", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "manual_payment"}},
                {"to_step": "handle_coming_soon", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },

        # 4a. Ask for transaction reference for manual payments
        {
            "name": "ask_for_transaction_ref",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "You've selected a manual payment. Please enter the transaction ID or receipt number for your contribution."
                    }
                },
                "reply_config": {
                    "save_to_variable": "transaction_ref",
                    "expected_type": "text"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Sorry, I didn't get that. Please enter the transaction reference number.",
                    "fallback_message_text": "Sorry, we couldn't process that. Please type 'give' to try again."
                }
            },
            "transitions": [
                {"to_step": "record_payment_action", "condition_config": {"type": "always_true"}}
            ]
        },

        # 4a. Handle methods that are not ready yet
        {
            "name": "handle_coming_soon",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "The payment method '{{ context.payment_method }}' is coming soon! Please select another method for now."}},
            "transitions": [{"to_step": "ask_payment_method", "condition_config": {"type": "always_true"}}]
        },

        # 4b. Record the payment using the action (for ALL valid methods)
        {
            "name": "record_payment_action",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "record_payment",
                    "amount_template": "{{ context.giving_amount }}",
                    "payment_type_template": "{{ context.payment_type }}",
                    "payment_method_template": "{{ context.payment_method }}",
                    "transaction_ref_template": "{{ context.transaction_ref }}",
                    "currency_template": "USD",
                    "notes_template": "Online giving via WhatsApp flow."
                }]
            },
            "transitions": [{"to_step": "end_giving", "condition_config": {"type": "always_true"}}]
        },
        
        # 5. End the flow
        {
            "name": "end_giving",
            "type": "end_flow",
            "config": {},
            "transitions": []
        }
    ]
}