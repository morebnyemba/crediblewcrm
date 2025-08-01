# whatsappcrm_backend/flows/definitions/sermons_flow.py
"""
This flow displays recent sermons to the user.
"""

SERMONS_FLOW = {
    "name": "view_sermons",
    "friendly_name": "View Recent Sermons",
    "description": "Shows a list of recent, published sermons.",
    "is_active": True,
    "steps": [
        {
            "name": "query_recent_sermons",
            "is_entry_point": True,
            "type": "action",
            "config": {
                "actions_to_run": [{
                    "action_type": "query_model",
                    "app_label": "church_services",
                    "model_name": "Sermon",
                    "variable_name": "sermons_list",
                    "filters_template": {"is_published": True},
                    "order_by": ["-sermon_date"],
                    "limit": 5
                }]
            },
            "transitions": [{"to_step": "show_sermons_list", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "show_sermons_list",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "{% if sermons_list %}Here are our most recent sermons:\n\n{% for sermon in sermons_list %}*{{ sermon.title }}*\n🗣️ {{ sermon.preacher }}\n🗓️ {{ sermon.sermon_date|strftime('%b %d, %Y') }}\n{% if sermon.video_link %}📺 Watch: {{ sermon.video_link }}{% endif %}\n\n{% endfor %}{% else %}There are no recent sermons available at the moment. Please check back soon!{% endif %}",
                    "preview_url": True
                }
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
