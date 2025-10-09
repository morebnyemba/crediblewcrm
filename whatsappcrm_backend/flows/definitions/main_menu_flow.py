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
        # 1. Check if user is registered to show the correct menu
        {
            "name": "check_if_registered_for_menu",
            "is_entry_point": True,
            "type": "action",
            "config": {"actions_to_run": []},
            "transitions": [
                {"to_step": "show_main_menu_registered", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "member_profile.first_name"}},
                {"to_step": "show_main_menu_visitor", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },

        # 2a. Show menu for REGISTERED users
        {
            "name": "show_main_menu_registered",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {"type": "text", "text": "Church Main Menu"},
                        "body": {"text": "Welcome back, {{ member_profile.first_name or 'member' }}! 🙏\n\nHow can we serve you today?"},
                        "footer": {"text": "Powered by crediblebrands.co.zw"},
                        "action": {
                            "button": "Show Menu",
                            "sections": [
                                {
                                    "title": "My Profile & Giving",
                                    "rows": [
                                        {"id": "go_to_profile_summary", "title": "Check My Profile", "description": "View your current information."},
                                        {"id": "trigger_registration_flow", "title": "Update My Profile", "description": "Change your registration details."},
                                        {"id": "give_online", "title": "Give Online", "description": "Support our ministry through tithes & offerings."}
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
                                    "title": "Get Involved",
                                    "rows": [
                                        {"id": "view_upcoming_events", "title": "Upcoming Events", "description": "See what's happening at our church."},
                                        {"id": "explore_ministries", "title": "Ministries & Groups", "description": "Find a group to connect with."}
                                    ]
                                },
                                {
                                    "title": "Support",
                                    "rows": [
                                        {"id": "talk_to_pastor", "title": "Talk to a Pastor", "description": "Request a conversation with our leadership."}
                                    ]
                                },
                                {
                                    "title": "About This Service",
                                    "rows": [
                                        {"id": "show_dev_info", "title": "Development Info", "description": "Learn more about the creators of this service."}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "selected_menu_option", "expected_type": "interactive_id"},
                "fallback_config": {
                    "action": "re_prompt", "max_retries": 1,
                    "re_prompt_message_text": "Sorry, that's not a valid selection. Please choose an option from the menu.",
                    "fallback_message_text": "If you need help, just type 'menu' to see the options again."
                }
            },
            "transitions": [
                {"to_step": "switch_to_registration", "condition_config": {"type": "interactive_reply_id_equals", "value": "trigger_registration_flow"}},
                {"to_step": "switch_to_prayer_request", "condition_config": {"type": "interactive_reply_id_equals", "value": "submit_prayer_request"}},
                {"to_step": "switch_to_giving", "condition_config": {"type": "interactive_reply_id_equals", "value": "give_online"}},
                {"to_step": "confirm_pastor_handover", "condition_config": {"type": "interactive_reply_id_equals", "value": "talk_to_pastor"}},
                {"to_step": "show_profile_summary", "condition_config": {"type": "interactive_reply_id_equals", "value": "go_to_profile_summary"}},
                {"to_step": "switch_to_events", "condition_config": {"type": "interactive_reply_id_equals", "value": "view_upcoming_events"}},
                {"to_step": "switch_to_ministries", "condition_config": {"type": "interactive_reply_id_equals", "value": "explore_ministries"}},
                {"to_step": "switch_to_sermons", "condition_config": {"type": "interactive_reply_id_equals", "value": "watch_recent_sermons"}},
                {"to_step": "display_dev_info", "condition_config": {"type": "interactive_reply_id_equals", "value": "show_dev_info"}},
            ]
        },

        # 2b. Show menu for GUEST users
        {
            "name": "show_main_menu_visitor",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {"type": "text", "text": "Church Main Menu"},
                        "body": {"text": "Hello {{ contact.name or 'there' }}! 🙏\n\nWelcome to our digital church home. How can we serve you today? Please choose an option from our main menu below."},
                        "footer": {"text": "Powered by crediblebrands.co.zw"},
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
                                },
                                {
                                    "title": "About This Service",
                                    "rows": [
                                        {"id": "show_dev_info", "title": "Development Info", "description": "Learn more about the creators of this service."}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "selected_menu_option", "expected_type": "interactive_id"},
                "fallback_config": {
                    "action": "re_prompt", "max_retries": 1,
                    "re_prompt_message_text": "Sorry, that's not a valid selection. Please choose an option from the menu.",
                    "fallback_message_text": "If you need help, just type 'menu' to see the options again."
                }
            },
            "transitions": [
                {"to_step": "switch_to_registration", "condition_config": {"type": "interactive_reply_id_equals", "value": "trigger_registration_flow"}},
                {"to_step": "switch_to_prayer_request", "condition_config": {"type": "interactive_reply_id_equals", "value": "submit_prayer_request"}},
                {"to_step": "switch_to_giving", "condition_config": {"type": "interactive_reply_id_equals", "value": "give_online"}},
                {"to_step": "confirm_pastor_handover", "condition_config": {"type": "interactive_reply_id_equals", "value": "talk_to_pastor"}},
                {"to_step": "prompt_to_register", "condition_config": {"type": "interactive_reply_id_equals", "value": "go_to_profile_summary"}}, # Visitor selected check profile - prompt them to register
                {"to_step": "switch_to_events", "condition_config": {"type": "interactive_reply_id_equals", "value": "view_upcoming_events"}},
                {"to_step": "switch_to_ministries", "condition_config": {"type": "interactive_reply_id_equals", "value": "explore_ministries"}},
                {"to_step": "switch_to_sermons", "condition_config": {"type": "interactive_reply_id_equals", "value": "watch_recent_sermons"}},
                {"to_step": "display_dev_info", "condition_config": {"type": "interactive_reply_id_equals", "value": "show_dev_info"}},
            ]
        },

        # --- Steps for Switching Flows ---
        {
            "name": "switch_to_registration",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "member_registration",
                "trigger_keyword_to_pass": "start_registration"
            },
            "transitions": []
        },
        {
            "name": "switch_to_prayer_request",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "prayer_request",
                "trigger_keyword_to_pass": "start_prayer_request"
            },
            "transitions": []
        },
        {
            "name": "switch_to_giving",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "giving",
                "trigger_keyword_to_pass": "start_giving"
            },
            "transitions": []
        },
        {
            "name": "switch_to_events",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "view_events",
                "trigger_keyword_to_pass": "start_events"
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
            "name": "switch_to_ministries",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "view_ministries",
                "trigger_keyword_to_pass": "start_ministries"
            },
            "transitions": []
        },
        {
            "name": "switch_to_sermons",
            "type": "switch_flow",
            "config": {
                "target_flow_name": "view_sermons",
                "trigger_keyword_to_pass": "start_sermons"
            },
            "transitions": []
        },

        # --- Confirm Human Handover (Talk to a Pastor) ---
        {
            "name": "confirm_pastor_handover",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "You've requested to speak with a pastor. Please note that during this time, the bot will not be able to assist you.\n\nWould you like to proceed or cancel?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "proceed_handover", "title": "Proceed"}},
                                {"type": "reply", "reply": {"id": "cancel_handover", "title": "Cancel"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "handover_confirmation", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "notify_pastors_of_handover", "condition_config": {"type": "interactive_reply_id_equals", "value": "proceed_handover"}},
                {"to_step": "offer_return_to_menu", "condition_config": {"type": "interactive_reply_id_equals", "value": "cancel_handover"}}
            ]
        },

        # --- NEW STEP: Notify Pastors via Action Step ---
        {
            "name": "notify_pastors_of_handover",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "send_admin_notification",
                        "message_template": "New pastor intervention request from {{ contact.name or contact.whatsapp_id }}. Please attend to them in the CRM.",
                        "notify_groups": ["Pastoral Team"]
                    }
                ]
            },
            "transitions": [
                {"to_step": "initiate_pastor_handover", "condition_config": {"type": "always_true"}}
            ]
        },

        # --- Step for Human Handover (Simplified) ---
        {
            "name": "initiate_pastor_handover",
            "type": "human_handover",
            "config": {"pre_handover_message_text": "One moment please, I'm connecting you to a pastor who will be with you shortly."},
            "transitions": []
        },

        # --- Profile Summary Path ---
        {
            "name": "show_profile_summary",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": (
                        "Here is your profile summary:\n\n"
                        "*Full Name:* {{ member_profile.first_name or 'N/A' }} {{ member_profile.last_name or '' }}\n"
                        "*Email:* {{ member_profile.email or 'N/A' }}\n"
                        "*Date of Birth:* {{ member_profile.date_of_birth or 'N/A' }}\n"
                        "*Marital Status:* {{ (member_profile.marital_status | replace('_', ' ') | title) or 'N/A' }}\n\n"
                        "--- Church Details ---\n"
                        "*Membership Status:* {{ (member_profile.membership_status | replace('_', ' ') | title) or 'N/A' }}\n"
                        "*Date Joined:* {{ member_profile.date_joined or 'N/A' }}\n"
                        "*Baptism Date:* {{ member_profile.baptism_date or 'N/A' }}\n\n"
                        "If any details are incorrect, you can select 'Update My Profile' from the main menu."
                    )
                }
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "prompt_to_register",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "It looks like your profile is incomplete. Please register first to view your summary.\n\nType 'register' to begin, or 'menu' to go back."}},
            "transitions": [{"to_step": "end_flow_silently", "condition_config": {"type": "always_true"}}]
        },

        # --- New step for Development Info ---
        {
            "name": "display_dev_info",
            "type": "send_message",
            "config": {
                "message_type": "text",
                "text": {
                    "body": "This system was proudly developed by Credible Brand's Partner, Slyker Tech Web Services.\n\n*Contact Us on WhatsApp:*\n*Credible Brands:* https://wa.me/263772519128?text=Hello%2C%20I'm%20inquiring%20about%20the%20AutoWhatsapp%20service.\n*Slyker Tech:* https://wa.me/263787211325?text=Hello%2C%20I'm%20inquiring%20about%20the%20AutoWhatsapp%20service.",
                    "preview_url": True
                }
            },
            "transitions": [{"to_step": "offer_return_to_menu", "condition_config": {"type": "always_true"}}]
        },

        # --- Looping and Ending (Loopback point updated) ---
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
                                {"type": "reply", "reply": {"id": "return_to_menu", "title": "Yes, show menu"}},
                                {"type": "reply", "reply": {"id": "end_conversation", "title": "No, I'm done"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "return_choice", "expected_type": "interactive_id"}
            },
            "transitions": [
                {"to_step": "check_if_registered_for_menu", "condition_config": {"type": "interactive_reply_id_equals", "value": "return_to_menu"}},
                {"to_step": "say_goodbye", "condition_config": {"type": "interactive_reply_id_equals", "value": "end_conversation"}}
            ]
        },
        {
            "name": "say_goodbye",
            "type": "send_message",
            "config": {"message_type": "text", "text": {"body": "You're welcome! Have a blessed day. 🙏"}},
            "transitions": [{"to_step": "end_flow_silently", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "end_flow_silently",
            "type": "end_flow",
            "config": {},
            "transitions": []
        }
    ]
}
