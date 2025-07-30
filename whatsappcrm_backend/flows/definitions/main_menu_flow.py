# whatsappcrm_backend/flows/definitions/main_menu_flow.py

"""
This flow definition provides a main menu for users to navigate to different
parts of the application, such as registration or checking their profile.
"""

MAIN_MENU_FLOW = {
    "name": "main_menu",
    "friendly_name": "Main Menu",
    "description": "Displays the main menu and handles user navigation.",
    "trigger_keywords": ["menu", "help", "options", "hi", "hello"],
    "is_active": True,
    "steps": [
        # 1. Show the main menu as an interactive list
        {
            "name": "show_main_menu",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {
                            "type": "text",
                            "text": "Main Menu"
                        },
                        "body": {
                            "text": "Hello {{ contact.name }}! 👋\n\nHow can I help you today? Please choose an option from the menu below."
                        },
                        "footer": {
                            "text": "Powered by AutoWhats"
                        },
                        "action": {
                            "button": "Show Options",
                            "sections": [
                                {
                                    "title": "Available Options",
                                    "rows": [
                                        {"id": "trigger_registration_flow", "title": "Register as a New Member", "description": "Create your profile with us."},
                                        {"id": "go_to_profile_summary", "title": "Check My Profile", "description": "View your current profile information."},
                                        {"id": "trigger_human_handover", "title": "Talk to a Human", "description": "Get assistance from one of our agents."}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "selected_menu_option",
                    "expected_type": "interactive_id"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 1,
                    "re_prompt_message_text": "Sorry, that's not a valid selection. Please choose an option from the menu.",
                    "fallback_message_text": "If you need help, just type 'menu' again."
                }
            },
            "transitions": [
                {
                    "to_step": "switch_to_registration",
                    "priority": 10,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "trigger_registration_flow"
                    }
                },
                {
                    "to_step": "show_profile_summary",
                    "priority": 10,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "go_to_profile_summary"
                    }
                },
                {
                    "to_step": "initiate_human_handover",
                    "priority": 10,
                    "condition_config": {
                        "type": "interactive_reply_id_equals",
                        "value": "trigger_human_handover"
                    }
                }
            ]
        },

        # 2a. Action step to switch to the registration flow
        {
            "name": "switch_to_registration",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "switch_flow",
                        "target_flow_name": "member_registration"
                    }
                ]
            },
            "transitions": [] # No transition needed, as the flow is switched internally
        },

        # 2b. Step to show the user's profile summary
        {
            "name": "show_profile_summary",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "Here is your profile summary:\n\n*Name:* {{ member_profile.first_name }} {{ member_profile.last_name }}\n*Email:* {{ member_profile.email }}\n*City:* {{ member_profile.city }}\n\nType 'menu' to return to the main menu."
                }
            },
            "transitions": [
                {
                    "to_step": "end_menu_flow",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },

        # 2c. Step to initiate a human handover
        {
            "name": "initiate_human_handover",
            "type": "human_handover",
            "config": {
                "pre_handover_message_text": "One moment please, I'm connecting you to a human agent who will be with you shortly."
            },
            "transitions": [] # This step automatically ends the flow
        },

        # 3. A common end point for paths that don't switch flows
        {
            "name": "end_menu_flow",
            "type": "end_flow",
            "config": {}, # No final message needed
            "transitions": []
        }
    ]
}