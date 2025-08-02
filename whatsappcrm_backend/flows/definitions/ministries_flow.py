# whatsappcrm_backend/flows/definitions/ministries_flow.py
"""
This flow displays a list of active ministries, one at a time,
allowing them to navigate through the list.
"""

MINISTRIES_FLOW = {
    "name": "view_ministries",
    "friendly_name": "View Ministries & Groups",
    "description": "Shows a list of active ministries and groups one by one.",
    "is_active": True,
    "steps": [
        {
            "name": "query_ministries",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "query_model",
                        "app_label": "church_services",
                        "model_name": "Ministry",
                        "variable_name": "ministries_list",
                        "filters_template": {"is_active": True},
                        "order_by": ["name"],
                        "limit": 10
                    },
                    {
                        "action_type": "set_context_variable",
                        "variable_name": "ministry_index",
                        "value_template": 0
                    }
                ]
            },
            "transitions": [{"to_step": "check_if_ministries_exist", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "check_if_ministries_exist",
            "type": "action",
            "config": {"actions_to_run": []},
            "transitions": [
                {"to_step": "display_ministry", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "ministries_list.0"}},
                {"to_step": "no_ministries_message", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "no_ministries_message",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "We don't have a list of ministries available at the moment. Please check back soon!"}},
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "display_ministry",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "Ministry ({{ (ministry_index | int) + 1 }} of {{ ministries_list|length }}):\n\n"
                        "*{{ ministries_list[ministry_index].name }}*\n"
                        "Leader: {{ ministries_list[ministry_index].leader_name }}\n"
                        "Schedule: {{ ministries_list[ministry_index].meeting_schedule }}\n\n"
                        "_{{ ministries_list[ministry_index].description|truncatewords(35) }}_"
                    )
                }
            },
            "transitions": [{"to_step": "ask_next_ministry_action", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_next_ministry_action",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "What would you like to do next?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "next_ministry", "title": "Next Ministry"}},
                                {"type": "reply", "reply": {"id": "return_to_menu", "title": "Main Menu"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "ministry_nav_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "increment_ministry_index", "priority": 10, "condition_config": {"type": "interactive_reply_id_equals", "value": "next_ministry"}},
                {"to_step": "switch_to_main_menu", "priority": 20, "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}}
            ]
        },
        {
            "name": "increment_ministry_index",
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "set_context_variable",
                    "variable_name": "ministry_index",
                    "value_template": "{{ (ministry_index | int) + 1 }}"
                }]
            },
            "transitions": [
                {"to_step": "display_ministry", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "ministries_list.{{ ministry_index }}"}},
                {"to_step": "end_of_ministries", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "end_of_ministries",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "You've reached the end of our ministries list!"}},
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
