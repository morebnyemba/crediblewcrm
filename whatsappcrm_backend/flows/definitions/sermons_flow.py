# whatsappcrm_backend/flows/definitions/sermons_flow.py
"""
This flow displays recent sermons to the user, one at a time,
allowing them to navigate through the list.
"""

SERMONS_FLOW = {
    "name": "view_sermons",
    "friendly_name": "View Recent Sermons",
    "description": "Shows a list of recent, published sermons one by one.",
    "is_active": True,
    "steps": [
        {
            "name": "query_recent_sermons",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "query_model",
                        "app_label": "church_services",
                        "model_name": "Sermon",
                        "variable_name": "sermons_list",
                        "filters_template": {"is_published": True},
                        "order_by": ["-sermon_date"],
                        "limit": 10
                    },
                    {
                        "action_type": "set_context_variable",
                        "variable_name": "sermon_index",
                        "value_template": 0
                    }
                ]
            },
            "transitions": [{"to_step": "check_if_sermons_exist", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "check_if_sermons_exist",
            "type": "action",
            "config": {"actions_to_run": []}, # This is a routing step
            "transitions": [
                {"to_step": "display_sermon", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "sermons_list.0"}},
                {"to_step": "no_sermons_message", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "no_sermons_message",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {"body": "There are no recent sermons available at the moment. Please check back soon!"}
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "display_sermon",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "Sermon ({{ (sermon_index | int) + 1 }} of {{ sermons_list|length }}):\n\n"
                        "*{{ sermons_list[sermon_index | int].title }}*\n"
                        "🗣️ Speaker: {{ sermons_list[sermon_index | int].preacher }}\n"
                        "🗓️ Date: {{ sermons_list[sermon_index | int].sermon_date|strftime('%b %d, %Y') }}\n\n"
                        "_{{ sermons_list[sermon_index | int].description|truncatewords(35) }}_\n\n"
                        "{% if sermons_list[sermon_index | int].video_link %}📺 Watch here: {{ sermons_list[sermon_index | int].video_link }}{% endif %}"
                    ),
                    "preview_url": True
                }
            },
            "transitions": [{"to_step": "ask_next_sermon_action", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_next_sermon_action",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "What would you like to do next?"},
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": "next_sermon", "title": "Next Sermon"}
                                },
                                {
                                    "type": "reply",
                                    "reply": {"id": "return_to_menu", "title": "Main Menu"}
                                }
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "sermon_nav_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "increment_sermon_index", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "next_sermon"}},
                {"to_step": "switch_to_main_menu", "priority": 20, "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}}
            ]
        },
        {
            "name": "increment_sermon_index",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "set_context_variable",
                    "variable_name": "sermon_index",
                    "value_template": "{{ (sermon_index | int) + 1 }}"
                }]
            },
            "transitions": [
                {"to_step": "display_sermon", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "sermons_list.{{ sermon_index }}"}},
                {"to_step": "end_of_sermons", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "end_of_sermons",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "You've reached the end of our recent sermons list!"}},
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
