# whatsappcrm_backend/flows/definitions/invalid_input_flow.py

"""
A generic flow to handle invalid user input from any other flow.
It presents the user with clear options on how to proceed.
"""

INVALID_INPUT_FLOW = {
    "name": "invalid_input_flow",
    "friendly_name": "Invalid Input Handler",
    "description": "Handles invalid user input by offering choices: retry, menu, or human help.",
    "trigger_keywords": [],  # This flow is only triggered internally
    "is_active": True,
    "steps": [
        {
            "name": "show_fallback_options",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {
                            "text": (
                                "I'm sorry, I didn't quite understand your last response. "
                                "What would you like to do?"
                            )
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "reprompt", "title": "Try Again"}},
                                {"type": "reply", "reply": {"id": "main_menu", "title": "Main Menu"}},
                                {"type": "reply", "reply": {"id": "human_handover", "title": "Talk to a Person"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "fallback_choice",
                    "expected_type": "interactive_id"
                }
            },
            "transitions": [
                {
                    "to_step": "switch_back_to_original_flow",
                    "condition_config": {"type": "interactive_reply_id_equals", "value": "reprompt"}
                },
                {
                    "to_step": "switch_to_main_menu",
                    "condition_config": {"type": "interactive_reply_id_equals", "value": "main_menu"}
                },
                {
                    "to_step": "initiate_human_handover",
                    "condition_config": {"type": "interactive_reply_id_equals", "value": "human_handover"}
                }
            ]
        },
        {
            "name": "switch_back_to_original_flow",
            "type": "switch_flow",
            "config": {
                # The original_flow_name and original_step_name are passed in the context
                # when this fallback flow is triggered.
                "target_flow_name": "{{ original_flow_name }}",
                "initial_context_template": {
                    # Pass back the original context, but also set a special keyword
                    # to tell the target flow to re-prompt the original question.
                    **"{{ original_context }}",
                    "simulated_trigger_keyword": "reprompt_step_{{ original_step_name }}"
                }
            },
            "transitions": []
        },
        {
            "name": "switch_to_main_menu",
            "type": "switch_flow",
            "config": {"target_flow_name": "main_menu"},
            "transitions": []
        },
        {
            "name": "initiate_human_handover",
            "type": "human_handover",
            "config": {
                "pre_handover_message_text": "No problem. I'm connecting you to a team member who can assist you shortly. Please wait a moment.",
                "notification_details": (
                    "Fallback Handover Request:\n\n"
                    "*Contact:* {{ contact.name or contact.whatsapp_id }}\n"
                    "*Original Flow:* {{ original_flow_name }}\n"
                    "*Original Step:* {{ original_step_name }}\n\n"
                    "User requested human assistance after providing invalid input."
                ),
                "notify_groups": ["Pastoral Team", "Technical Admin"]
            },
            "transitions": []
        }
    ]
}

