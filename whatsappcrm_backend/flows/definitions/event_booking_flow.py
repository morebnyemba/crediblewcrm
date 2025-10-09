# whatsappcrm_backend/flows/definitions/event_booking_flow.py

EVENT_BOOKING_FLOW = {
    "name": "event_booking",
    "friendly_name": "Event Booking",
    "description": "Handles a user's request to book a spot for an event.",
    "trigger_keywords": ["book_event"], # Internal trigger
    "is_active": True,
    "steps": [
        {
            "name": "confirm_booking",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": "You're about to register for the event: *{{ event_title }}*.\n\nCan you confirm you'd like to book your spot?"
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
                {"to_step": "record_booking_action", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_booking_yes"}},
                {"to_step": "booking_cancelled", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_booking_no"}}
            ]
        },
        {
            "name": "record_booking_action",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "record_event_booking",
                        "event_id_template": "{{ event_id }}",
                        "status_template": "confirmed"
                    }
                ]
            },
            "transitions": [
                {"to_step": "notify_admin_of_booking", "priority": 10, "condition_config": {"type": "variable_equals", "variable_name": "event_booking_success", "value": "True"}},
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
                    "message_template": "New Event Booking:\n\n*Event:* {{ event_title }}\n*Who:* {{ contact.name or contact.whatsapp_id }}\n\nThey have been successfully registered."
                }]
            },
            "transitions": [{"to_step": "booking_confirmed", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "booking_confirmed",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {"body": "Excellent! You are now registered for *{{ event_title }}*. We look forward to seeing you there! 🎉"}
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