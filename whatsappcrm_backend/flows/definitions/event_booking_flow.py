# whatsappcrm_backend/flows/definitions/event_booking_flow.py

"""
This flow handles event booking, including a conditional payment step
for events that have a registration fee.
"""

EVENT_BOOKING_FLOW = {
    "name": "event_booking",
    "friendly_name": "Event Booking",
    "description": "Handles a user's request to book a spot for an event.",
    "trigger_keywords": ["book_event"], # Internal trigger
    "is_active": True,
    "steps": [
        # 1. Check if the event has a fee to decide the path.
        # NEW: Ask for number of tickets first.
        {
            "name": "ask_for_number_of_tickets",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "How many tickets would you like to book for *{{ event_title }}*?"}
                },
                "reply_config": {
                    "expected_type": "number",
                    "save_to_variable": "number_of_tickets",
                    "validation_regex": "^[1-9][0-9]*$"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Please enter a valid number (e.g., 1, 2, 5)."
                }
            },
            "transitions": [{"to_step": "calculate_total_fee", "condition_config": {"type": "always_true"}}]
        },
        # NEW: Calculate total fee and then check if it's a paid event.
        {
            "name": "calculate_total_fee",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "set_context_variable",
                    "variable_name": "total_fee",
                    "value_template": "{{ (event_fee | float) * (number_of_tickets | int) }}"
                }]
            },
            "transitions": [
                # If event_fee is greater than 0, go to the paid flow.
                {"to_step": "confirm_paid_booking", "priority": 10, "condition_config": {"type": "variable_greater_than", "variable_name": "total_fee", "value": 0}},
                # Otherwise, go to the free booking confirmation.
                {"to_step": "confirm_free_booking", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        # --- Path for FREE events ---
        {
            "name": "confirm_free_booking",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "You're about to book *{{ number_of_tickets }} ticket(s)* for the free event: *{{ event_title }}*.\n\nCan you confirm?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_booking_yes", "title": "Yes, Confirm"}},
                                {"type": "reply", "reply": {"id": "confirm_booking_no", "title": "No, Cancel"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "booking_confirmation",
                    "expected_type": "interactive_id"
                }
            },
            "transitions": [
                {"to_step": "record_free_booking_action", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_booking_yes"}},
                {"to_step": "booking_cancelled", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_booking_no"}}
            ]
        },
        # --- Path for PAID events ---
        {
            "name": "confirm_paid_booking",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "To register for *{{ event_title }}*, a payment of *${{      (total_fee | float) | round(2) }}* is required for *{{ number_of_tickets }} ticket(s)* (at ${{ event_fee }} each).\n\n"
                        "{% if event_payment_instructions %}"
                        "Please use the payment instructions provided by the event organizer below:\n\n"
                        "{{ event_payment_instructions }}\n\n"
                        "{% else %}"
                        "Please use one of the default church payment methods below:\n\n"
                        "🇺🇸 *International & USA*\n"
                        "1. *Bank of America*\n   - Routing: `061000052`\n   - Account: `3340 7458 7536`\n"
                        "2. *PayPal*\n   https://paypal.me/LifeInternational704\n"
                        "3. *Zelle*\n   `LifeInternationalusa@gmail.com`\n\n"
                        "🇿🇼 *Zimbabwe*\n"
                        "4. *EcoCash Merchant (USD/ZWG)*\n   Code: `030630`\n"
                        "5. *Agribank (ZWG)*\n   - Account: `100009498774`\n   - Branch: N. Mandela, Zimbabwe\n\n"
                        "{% endif %}"
                        "After paying, please send a screenshot as proof of payment to complete your registration."
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
                "to_step": "record_paid_booking_action",
                "condition_config": {"type": "variable_exists", "variable_name": "proof_of_payment_wamid"}
            }]
        },
        # --- Action Steps ---
        {
            "name": "record_paid_booking_action",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "record_event_booking",
                        "event_id_template": "{{ event_id }}",
                        "number_of_tickets_template": "{{ number_of_tickets }}",
                        "status_template": "pending_payment",
                        "notes_template": "Booking for {{ number_of_tickets }} ticket(s) pending proof of payment verification for ${{ total_fee | round(2) }}.",
                        "proof_of_payment_wamid_template": "{{ proof_of_payment_wamid }}"
                    }
                ]
            },
            "transitions": [{"to_step": "notify_admin_of_booking", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "record_free_booking_action",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "record_event_booking",
                        "event_id_template": "{{ event_id }}",
                        "number_of_tickets_template": "{{ number_of_tickets }}",
                        "status_template": "confirmed"
                    }
                ]
            },
            "transitions": [
                {"to_step": "booking_confirmed", "priority": 10, "condition_config": {"type": "variable_equals", "variable_name": "event_booking_success", "value": "True"}},
                {"to_step": "booking_failed", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "notify_admin_of_booking",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "send_admin_notification",
                    "notify_groups": ["Events Team", "Pastoral Team"],
                    "message_template": (
                        "New Event Booking (Payment Pending):\n\n*Event:* {{ event_title }}\n*Who:* {{ contact.name or contact.whatsapp_id }}\n*Tickets:* {{ number_of_tickets }}\n\n"
                        "They have submitted proof of payment for ${{ (total_fee | float) | round(2) }}. Please verify in the CRM to confirm their booking."
                    )
                }]
            },
            "transitions": [{"to_step": "booking_confirmed", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "booking_confirmed",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "{% if (total_fee | float) > 0 %}Thank you! Your registration for *{{ number_of_tickets }} ticket(s)* for *{{ event_title }}* is now pending verification. You will receive a final confirmation soon.{% else %}Excellent! You are now registered for *{{ number_of_tickets }} ticket(s)* for *{{ event_title }}*. We look forward to seeing you there! 🎉{% endif %}"
                    )
                }
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "booking_failed",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {"body": "Sorry, we couldn't process your booking for *{{ event_title }}* at this time. It's possible you are already registered.\n\nError: {{ event_booking_error }}"}
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "booking_cancelled",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "No problem. Your booking has been cancelled."}},
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "offer_return_to_menu",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "Would you like to return to the main menu?"},
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
        {"name": "switch_to_main_menu", "type": "switch_flow", "config": {"target_flow_name": "main_menu"}, "transitions": []},
        {"name": "end_flow_goodbye", "type": "end_flow", "config": {"message_config": {"message_type": "text", "text": {"body": "You're welcome! Have a blessed day."}}}, "transitions": []}
    ]
}