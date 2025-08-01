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
            "transitions": [{"to_step": "check_if_sermons_exist", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "check_if_sermons_exist",
            "type": "action",
            "config": {"actions_to_run": []},
            "transitions": [
                {"to_step": "show_sermons_list", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "sermons_list"}},
                {"to_step": "show_no_sermons_message", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },
        {
            "name": "show_sermons_list",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Here are our most recent sermons:\n\n{% for sermon in sermons_list %}*{{ sermon.title }}*\n🗣️ {{ sermon.preacher }}\n
