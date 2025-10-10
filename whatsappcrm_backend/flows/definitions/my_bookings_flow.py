# whatsappcrm_backend/flows/definitions/my_bookings_flow.py

"""
This flow allows users to view a list of their upcoming event bookings.
"""

MY_BOOKINGS_FLOW = {
    "name": "my_bookings",
    "friendly_name": "My Event Bookings",
    "description": "Shows a user their upcoming event bookings one by one.",
    "trigger_keywords": ["my bookings", "my events"],
    "is_active": True,
    "steps": [
        {
            "name": "query_my_bookings",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "query_model",
                        "app_label": "church_services",
                        "model_name": "EventBooking",
                        "variable_name": "bookings_list",
                        # Query for confirmed bookings for this contact for events starting in the future
                        "filters_template": {
                            "contact_id": "{{ contact.id }}",
                            "status": "confirmed",
                            "event__start_time__gte": "{{ now() }}"
                        },
                        "order_by": ["event__start_time"],
                        "limit": 10
                    },
                    {
                        "action_type": "set_context_variable",
                        "variable_name": "booking_index",
                        "value_template": 0
                    }
                ]
            },
            "transitions": [{"to_step": "check_if_bookings_exist", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "check_if_bookings_exist",
            "type": "action",
            "config": {"actions_to_run": []}, # Routing step
            "transitions": [
                {"to_step": "display_booking", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "bookings_list.0"}},
                {"to_step": "no_bookings_message", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "no_bookings_message",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {"body": "You don't have any upcoming event bookings at the moment. You can view and register for events from the main menu."}
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "display_booking",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "Your Booking ({{ (booking_index | int) + 1 }} of {{ bookings_list|length }}):\n\n"
                        # Note: Accessing related event details requires a change in how query_model works or a more complex template.
                        # For now, we assume the query can fetch related data or we make a second query.
                        # Let's assume for now we can access it simply. A better way is to enhance query_model.
                        "*{{ bookings_list[booking_index | int].event.title }}*\n"
                        "🗓️ When: {{ bookings_list[booking_index | int].event.start_time|strftime('%a, %b %d, %Y @ %I:%M %p') }}\n"
                        "📍 Where: {{ bookings_list[booking_index | int].event.location }}\n\n"
                        "Status: *{{ bookings_list[booking_index | int].status|title }}*"
                    )
                }
            },
            "transitions": [{"to_step": "ask_next_booking_action", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_next_booking_action",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "What would you like to do next?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "cancel_booking", "title": "Cancel This Booking"}},
                                {"type": "reply", "reply": {"id": "next_booking", "title": "Next Booking"}},
                                {"type": "reply", "reply": {"id": "return_to_menu", "title": "Main Menu"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "booking_nav_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "confirm_cancellation", "priority": 5, "condition_config": {"type": "interactive_reply_id_equals", "value": "cancel_booking"}},
                {"to_step": "increment_booking_index", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "next_booking"}},
                {"to_step": "end_flow_and_prompt_menu", "priority": 20, "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}}
            ]
        },
        {
            "name": "increment_booking_index",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "set_context_variable",
                    "variable_name": "booking_index",
                    "value_template": "{{ (booking_index | int) + 1 }}"
                }]
            },
            "transitions": [
                {"to_step": "display_booking", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "bookings_list.{{ booking_index }}"}},
                {"to_step": "end_of_bookings", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "end_of_bookings",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "You've reached the end of your bookings list."}},
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
                {"to_step": "end_flow_goodbye", "condition_config": {"type": "interactive_reply_id_equals", "value": "end_conversation"}},
            ]
        },
        # --- New Steps for Cancellation ---
        {
            "name": "confirm_cancellation",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "Are you sure you want to cancel your booking for *{{ bookings_list[booking_index | int].event.title }}*?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "cancel_yes", "title": "Yes, Cancel"}},
                                {"type": "reply", "reply": {"id": "cancel_no", "title": "Keep Booking"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "cancellation_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "process_cancellation", "condition_config": {"type": "interactive_reply_id_equals", "value": "cancel_yes"}},
                {"to_step": "ask_next_booking_action", "condition_config": {"type": "interactive_reply_id_equals", "value": "cancel_no"}}
            ]
        },
        {
            "name": "process_cancellation",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "update_model_record",
                        "app_label": "church_services",
                        "model_name": "EventBooking",
                        "filters_template": {"id": "{{ bookings_list[booking_index | int].id }}"},
                        "updates_template": {"status": "cancelled"}
                    },
                    {
                        "action_type": "send_admin_notification",
                        "notify_groups": ["Events Team"],
                        "message_template": "Booking Cancellation:\n\n*Event:* {{ bookings_list[booking_index | int].event.title }}\n*Who:* {{ contact.name or contact.whatsapp_id }}\n\nTheir booking has been cancelled."
                    }
                ]
            },
            "transitions": [{"to_step": "cancellation_confirmed_and_requery", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "cancellation_confirmed_and_requery",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {"body": "Your booking has been successfully cancelled."}
            },
            "transitions": [{"to_step": "query_my_bookings", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "switch_to_main_menu",
            "type": "switch_flow",
            "config": {"target_flow_name": "main_menu"},
            "transitions": []
        },
        # New step to end the flow and prompt user to type 'menu'
        {"name": "end_flow_and_prompt_menu", "type": "end_flow", "config": {"message_config": {"message_type": "text", "text": {"body": "Okay, you can type 'menu' at any time to return to the main menu."}}}, "transitions": []},

        {
            "name": "end_flow_goodbye",
            "type": "end_flow",
            "config": {"message_config": {"message_type": "text", "text": {"body": "You're welcome! Have a blessed day."}}},
            "transitions": []
        }
    ]
}