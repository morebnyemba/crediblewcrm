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
                "message_type": "text",
                "text": {
                    "body": (
                        "Upcoming Event ({{ event_index + 1 }} of {{ events_list|length }}):\n\n"
                        "*{{ events_list[event_index].title }}*\n"
                        "🗓️ When: {{ events_list[event_index].start_time|strftime('%a, %b %d, %Y @ %I:%M %p') }}\n"
                        "📍 Where: {{ events_list[event_index].location }}\n\n"
                        "_{{ events_list[event_index].description|truncatewords(35) }}_\n\n"
                        "{% if events_list[event_index].registration_link %}Register here: {{ events_list[event_index].registration_link }}{% endif %}"
                    )
                }
            },
            "transitions": [{"to_step": "ask_next_event_action", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_next_event_action",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "What would you like to do next?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "next_event", "title": "Next Event"}},
                                {"type": "reply", "reply": {"id": "return_to_menu", "title": "Main Menu"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "event_nav_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "increment_event_index", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "next_event"}},
                {"to_step": "switch_to_main_menu", "priority": 20, "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}}
            ]
        },
        {
            "name": "increment_event_index",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "set_context_variable",
                    "variable_name": "event_index",
                    "value_template": "{{ event_index + 1 }}"
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
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "switch_flow", "target_flow_name": "main_menu"}]},
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
    