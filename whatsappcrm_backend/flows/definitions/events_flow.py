"""
This flow displays upcoming events to the user, one at a time,
allowing them to navigate through the list.
"""

EVENTS_FLOW = {
    "name": "view_events",
    "friendly_name": "View Upcoming Events",
    "description": "Shows a list of active, upcoming events one by one.",
    "is_active": True,
    "steps": [
        {
            "name": "query_upcoming_events",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "query_model",
                        "app_label": "church_services",
                        "model_name": "Event",
                        "variable_name": "events_list", 
                        "filters_template": {"is_active": True, "start_time__gte": "{{ now() }}"},
                        "order_by": ["start_time"],
                        "limit": 10
                    },
                    {
                        "action_type": "set_context_variable",
                        "variable_name": "event_index",
                        "value_template": 0
                    }
                ]
            },
            "transitions": [{"to_step": "check_if_events_exist", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "check_if_events_exist",
            "type": "action",
            "config": {"actions_to_run": []}, # This is a routing step
            "transitions": [
                {"to_step": "display_event", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "events_list.0"}},
                {"to_step": "no_events_message", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "no_events_message",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {"body": "There are no upcoming events scheduled at the moment. Please check back soon!"}
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "display_event",
            "type": "send_message",
            "config": {
                # Use a Jinja 'if' to dynamically set the message type.
                # If a flyer exists, send an 'image' message. Otherwise, send 'text'.
                "message_type": "{% if events_list[event_index | int].flyer %}image{% else %}text{% endif %}",
                "image": {
                    "link": "{{ events_list[event_index | int].flyer }}",
                    "caption": (
                        "Upcoming Event ({{ (event_index | int) + 1 }} of {{ events_list|length }}):\n\n"
                        "*{{ events_list[event_index | int].title }}*\n"
                        "🗓️ When: {{ events_list[event_index | int].start_time|strftime('%a, %b %d, %Y @ %I:%M %p') }}\n"
                        "📍 Where: {{ events_list[event_index | int].location }}\n\n"
                        "_{{ events_list[event_index | int].description|truncatewords(35) }}_\n\n"
                        "{% if (events_list[event_index | int].registration_fee | float) > 0 %}Fee: ${{ events_list[event_index | int].registration_fee }}{% else %}Fee: Free{% endif %}\n"
                        "{% if events_list[event_index | int].registration_link %}More Info: {{ events_list[event_index | int].registration_link }}{% endif %}"
                    )
                },
                "text": {
                    # This 'body' is identical to the 'caption' above. It will only be used if the message_type resolves to 'text'.
                    "body": (
                        "Upcoming Event ({{ (event_index | int) + 1 }} of {{ events_list|length }}):\n\n*{{ events_list[event_index | int].title }}*\n🗓️ When: {{ events_list[event_index | int].start_time|strftime('%a, %b %d, %Y @ %I:%M %p') }}\n📍 Where: {{ events_list[event_index | int].location }}\n\n_{{ events_list[event_index | int].description|truncatewords(35) }}_\n\n{% if events_list[event_index | int].registration_link %}Register here: {{ events_list[event_index | int].registration_link }}{% endif %}"
                    )
                }
            },
            "transitions": [{"to_step": "check_if_location_exists", "condition_config": {"type": "always_true"}}]
        },

        {
            "name": "ask_next_event_action",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {"type": "text", "text": "Event Options"},
                        "body": {"text": "What would you like to do next?"},
                        "action": {
                            "button": "Choose an Option",
                            "sections": [
                                {
                                    "title": "Navigation",
                                    "rows": [
                                        {"id": "register_for_event", "title": "Register for this Event", "description": "Book your spot for the event shown above."},
                                        {"id": "my_bookings", "title": "My Bookings", "description": "View events you are already registered for."},
                                        {"id": "next_event", "title": "Next Event", "description": "See the next event in the list."},
                                        {"id": "return_to_menu", "title": "Main Menu", "description": "Go back to the main church menu."}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "event_nav_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "switch_to_event_booking", "priority": 5, "condition_config": {"type": "interactive_reply_id_equals", "value": "register_for_event"}},
                {"to_step": "switch_to_my_bookings", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "my_bookings"}},
                {"to_step": "increment_event_index", "priority": 15, "condition_config": {"type": "interactive_reply_id_equals", "value": "next_event"}},
                {"to_step": "switch_to_main_menu", "priority": 25, "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}}
            ]
        },
        {
            "name": "check_if_location_exists",
            "type": "action",
            "config": {"actions_to_run": []},
            "transitions": [
                {"to_step": "ask_get_directions", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "events_list[{{ event_index | int }}].latitude"}},
                {"to_step": "ask_next_event_action", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "ask_get_directions",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "We have a precise location for this event. Would you like to get directions?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "get_directions_yes", "title": "Get Directions"}},
                                {"type": "reply", "reply": {"id": "get_directions_no", "title": "Not Now"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "get_directions_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "send_location_pin", "condition_config": {"type": "interactive_reply_id_equals", "value": "get_directions_yes"}},
                {"to_step": "ask_next_event_action", "condition_config": {"type": "interactive_reply_id_equals", "value": "get_directions_no"}}
            ]
        },
        {
            "name": "increment_event_index",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "set_context_variable",
                    "variable_name": "event_index",
                    "value_template": "{{ (event_index | int) + 1 }}"
                }]
            },
            "transitions": [
                {"to_step": "display_event", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "events_list.{{ event_index }}"}},
                {"to_step": "end_of_events", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "end_of_events",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "You've reached the end of our upcoming events list!"}},
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
        {
            "name": "switch_to_main_menu",
            "type": "switch_flow",
            "config": {"target_flow_name": "main_menu"},
            "transitions": []
        },
        {
            "name": "send_location_pin",
            "type": "send_message",
            "config": {
                "message_type": "location",
                "location": {
                    "latitude": "{{ events_list[event_index | int].latitude }}",
                    "longitude": "{{ events_list[event_index | int].longitude }}",
                    "name": "{{ events_list[event_index | int].title }}",
                    "address": "{{ events_list[event_index | int].location }}"
                }
            },
            "transitions": [{"to_step": "ask_next_event_action", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "switch_to_event_booking",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "event_booking",
                "initial_context_template": {
                    "event_id": "{{ events_list[event_index | int].id }}",
                    "event_title": "{{ events_list[event_index | int].title }}",
                    "event_fee": "{{ events_list[event_index | int].registration_fee }}"
                }
            },
            "transitions": []
        },
        {
            "name": "switch_to_my_bookings",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "my_bookings",
                "trigger_keyword_to_pass": "my_bookings"
            },
            "transitions": []
        },
        {
            "name": "end_flow_goodbye",
            "type": "end_flow",
            "config": {"message_config": {"message_type": "text", "text": {"body": "You're welcome! Have a blessed day."}}},
            "transitions": []
        }
    ]
}
    