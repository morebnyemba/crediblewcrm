# whatsappcrm_backend/flows/definitions/ministries_flow.py
"""
This flow displays a list of active ministries.
"""

MINISTRIES_FLOW = {
    "name": "view_ministries",
    "friendly_name": "View Ministries & Groups",
    "description": "Shows a list of active ministries and groups.",
    "is_active": True,
    "steps": [
        {
            "name": "query_ministries",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "query_model",
                    "app_label": "church_services",
                    "model_name": "Ministry",
                    "variable_name": "ministries_list",
                    "filters_template": {"is_active": True},
                    "order_by": ["name"],
                    "limit": 10
                }]
            },
            "transitions": [{"to_step": "check_if_ministries_exist", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "check_if_ministries_exist",
            "type": "action",
            "config": {"actions_to_run": []},
            "transitions": [
                {"to_step": "show_ministries_list", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "ministries_list"}},
                {"to_step": "show_no_ministries_message", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "show_ministries_list",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Here are our available ministries:\n\n{% for ministry in ministries_list %}*{{ ministry.name }}*\nLeader: {{ ministry.leader_name }}\nSchedule: {{ ministry.meeting_schedule }}\n_{{ ministry.description|truncatewords:15 }}_\n\n{% endfor %}"
                }
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "show_no_ministries_message",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {"body": "We don't have a list of ministries available at the moment. Please check back soon!"}
            },
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
