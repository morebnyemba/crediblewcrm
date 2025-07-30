"""
This flow definition provides a main menu for users to navigate to different
parts of the application, such as registration, viewing events, or giving.
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
                            "text": "Church Main Menu"
                        },
                        "body": {
                            "text": "Hello {{ contact.name }}! 🙏\n\nWelcome to our digital church home. How can we serve you today? Please choose an option from our main menu below."
                        },
                        "footer": {
                            "text": "Powered by Credible Brands(credible.co.zw)"
                        },
                        "action": {
                            "button": "Show Menu",
                            "sections": [
                                {
                                    "title": "Get Involved",
                                    "rows": [
                                        {"id": "trigger_registration_flow", "title": "New Member Registration", "description": "Join our church family officially."},
                                        {"id": "view_upcoming_events", "title": "Upcoming Events", "description": "See what's happening at our church."},
                                        {"id": "explore_ministries", "title": "Ministries & Groups", "description": "Find a group to connect with."}
                                    ]
                                },
                                {
                                    "title": "Spiritual Growth",
                                    "rows": [
                                        {"id": "watch_recent_sermons", "title": "Recent Sermons", "description": "Catch up on the latest messages."},
                                        {"id": "submit_prayer_request", "title": "Submit a Prayer Request", "description": "Let us know how we can pray for you."}
                                    ]
                                },
                                {
                                    "title": "Giving & Support",
                                    "rows": [
                                        {"id": "give_online", "title": "Give Online", "description": "Support our ministry through tithes & offerings."},
                                        {"id": "talk_to_pastor", "title": "Talk to a Pastor", "description": "Request a conversation with our leadership."}
                                    ]
                                },
                                {
                                    "title": "My Profile",
                                    "rows": [
                                        {"id": "go_to_profile_summary", "title": "Check My Profile", "description": "View your current information."}
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
                    "fallback_message_text": "If you need help, just type 'menu' to see the options again."
                }
            },
            "transitions": [
                {"to_step": "switch_to_registration", "condition_config": {"type": "interactive_reply_id_equals", "value": "trigger_registration_flow"}},
                {"to_step": "show_profile_summary", "condition_config": {"type": "interactive_reply_id_equals", "value": "go_to_profile_summary"}},
                {"to_step": "show_upcoming_events", "condition_config": {"type": "interactive_reply_id_equals", "value": "view_upcoming_events"}},
                {"to_step": "show_ministries", "condition_config": {"type": "interactive_reply_id_equals", "value": "explore_ministries"}},
                {"to_step": "show_sermons", "condition_config": {"type": "interactive_reply_id_equals", "value": "watch_recent_sermons"}},
                {"to_step": "switch_to_prayer_request", "condition_config": {"type": "interactive_reply_id_equals", "value": "submit_prayer_request"}},
                {"to_step": "switch_to_giving", "condition_config": {"type": "interactive_reply_id_equals", "value": "give_online"}},
                {"to_step": "initiate_pastor_handover", "condition_config": {"type": "interactive_reply_id_equals", "value": "talk_to_pastor"}},
            ]
        },

        # 2a. Action to switch to the registration flow
        {
            "name": "switch_to_registration",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "switch_flow", "target_flow_name": "member_registration"}]},
            "transitions": []
        },

        # 2b. Show profile summary
        {
            "name": "show_profile_summary",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "Here is your profile summary:\n\n*Name:* {{ member_profile.first_name }} {{ member_profile.last_name }}\n*Email:* {{ member_profile.email }}\n*City:* {{ member_profile.city }}\n\nType 'menu' to return to the main menu."}},
            "transitions": [{"to_step": "end_menu_flow", "condition_config": {"type": "always_true"}}]
        },

        # 2c. Placeholder for upcoming events
        {
            "name": "show_upcoming_events",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "Here are our upcoming events... (feature coming soon).\n\nType 'menu' to return."}},
            "transitions": [{"to_step": "end_menu_flow", "condition_config": {"type": "always_true"}}]
        },

        # 2d. Placeholder for ministries
        {
            "name": "show_ministries",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "Here are our ministries and groups... (feature coming soon).\n\nType 'menu' to return."}},
            "transitions": [{"to_step": "end_menu_flow", "condition_config": {"type": "always_true"}}]
        },

        # 2e. Placeholder for sermons
        {
            "name": "show_sermons",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "Here are our recent sermons... (feature coming soon).\n\nType 'menu' to return."}},
            "transitions": [{"to_step": "end_menu_flow", "condition_config": {"type": "always_true"}}]
        },

        # 2f. Action to switch to the prayer request flow
        {
            "name": "switch_to_prayer_request",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "switch_flow", "target_flow_name": "prayer_request"}]},
            "transitions": []
        },

        # 2g. Action to switch to the giving flow
        {
            "name": "switch_to_giving",
            "type": "action",
            "config": {"actions_to_run": [{"action_type": "switch_flow", "target_flow_name": "giving"}]},
            "transitions": []
        },

        # 2h. Initiate human handover to a pastor
        {
            "name": "initiate_pastor_handover",
            "type": "human_handover",
            "config": {"pre_handover_message_text": "One moment please, I'm connecting you to a pastor who will be with you shortly."},
            "transitions": []
        },

        # 3. Common end point
        {
            "name": "end_menu_flow",
            "type": "end_flow",
            "config": {},
            "transitions": []
        }
    ]
}
