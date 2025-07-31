# whatsappcrm_backend/flows/definitions/registration_flow.py

"""
This flow definition collects all the necessary data to create a MemberProfile.
It uses various message types for a better user experience and concludes
by using an 'action' step to persist the data.
"""

REGISTRATION_FLOW = {
    "name": "member_registration",
    "friendly_name": "New Member Registration",
    "description": "Collects information to create a new member profile.",
    "trigger_keywords": ["register", "join", "signup"],
    "is_active": True,
    "steps": [
        # 1. Check if a profile already exists to decide whether to register or update.
        {
            "name": "check_existing_profile",
            "is_entry_point": True,
            "type": "action",
            "config": {"actions_to_run": []},
            "transitions": [
                {"to_step": "confirm_update_profile", "priority": 10, "condition_config": {"type": "variable_exists", "variable_name": "member_profile.first_name"}},
                {"to_step": "start_registration", "priority": 20, "condition_config": {"type": "always_true"}}
            ]
        },

        # 2a. If profile exists, ask the user if they want to update it.
        {
            "name": "confirm_update_profile",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "Hi {{ member_profile.first_name }}! It looks like you're already registered. Would you like to update your information now?"},
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "start_update", "title": "Yes, update info"}},
                                {"type": "reply", "reply": {"id": "cancel_update", "title": "No, cancel"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "update_choice", "expected_type": "interactive_id"},
                "fallback_config": {
                    "action": "re_prompt", "max_retries": 1,
                    "re_prompt_message_text": "Please tap one of the buttons to continue."
                }
            },
            "transitions": [
                {"to_step": "load_existing_profile_to_context", "condition_config": {"type": "interactive_reply_id_equals", "value": "start_update"}},
                {"to_step": "end_flow_cancelled", "condition_config": {"type": "interactive_reply_id_equals", "value": "cancel_update"}}
            ]
        },

        # NEW: Load existing data into context for a smoother update experience
        {
            "name": "load_existing_profile_to_context",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {"action_type": "set_context_variable", "variable_name": "first_name", "value_template": "{{ member_profile.first_name }}"},
                    {"action_type": "set_context_variable", "variable_name": "last_name", "value_template": "{{ member_profile.last_name }}"},
                    {"action_type": "set_context_variable", "variable_name": "gender", "value_template": "{{ member_profile.gender }}"},
                    {"action_type": "set_context_variable", "variable_name": "marital_status", "value_template": "{{ member_profile.marital_status }}"},
                    {"action_type": "set_context_variable", "variable_name": "date_of_birth", "value_template": "{{ member_profile.date_of_birth }}"},
                    {"action_type": "set_context_variable", "variable_name": "email", "value_template": "{{ member_profile.email }}"},
                    {"action_type": "set_context_variable", "variable_name": "city", "value_template": "{{ member_profile.city }}"}
                ]
            },
            "transitions": [{"to_step": "start_registration", "condition_config": {"type": "always_true"}}]
        },

        # 3. Start the registration/update process.
        {
            "name": "start_registration",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Welcome! To register or update your profile, I just need to ask a few quick questions.\n\nLet's start with your first name."
                    }
                },
                "reply_config": {
                    "save_to_variable": "first_name",
                    "expected_type": "text"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "I didn't quite get that. Please enter your first name."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_last_name",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        # 4. Subsequent data collection steps...
        {
            "name": "ask_last_name",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Great, {{ first_name }}! What is your last name?"
                    }
                },
                "reply_config": {
                    "save_to_variable": "last_name",
                    "expected_type": "text"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Sorry, I didn't catch that. Please enter your last name."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_gender",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        {
            "name": "ask_gender",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {
                            "type": "text",
                            "text": "Gender Selection"
                        },
                        "body": {
                            "text": "Please select your gender from the list below."
                        },
                        "action": {
                            "button": "Select Gender",
                            "sections": [
                                {
                                    "title": "Options",
                                    "rows": [
                                        {"id": "male", "title": "Male"},
                                        {"id": "female", "title": "Female"},
                                        {"id": "other", "title": "Other"},
                                        {"id": "prefer_not_to_say", "title": "Prefer not to say"}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "gender",
                    "expected_type": "interactive_id"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 1,
                    "re_prompt_message_text": "Please make a selection from the list to continue."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_marital_status",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        {
            "name": "ask_marital_status",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {"type": "text", "text": "Marital Status"},
                        "body": {"text": "What is your marital status?"},
                        "action": {
                            "button": "Select Status",
                            "sections": [{
                                "title": "Options",
                                "rows": [
                                    {"id": "single", "title": "Single"},
                                    {"id": "married", "title": "Married"},
                                    {"id": "divorced", "title": "Divorced"},
                                    {"id": "widowed", "title": "Widowed"}
                                ]
                            }]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "marital_status",
                    "expected_type": "interactive_id"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 1,
                    "re_prompt_message_text": "Please make a selection from the list to continue."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_dob",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        {
            "name": "ask_dob",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "What is your date of birth?\n\nPlease use the format YYYY-MM-DD (e.g., 1990-05-21)."}
                },
                "reply_config": {
                    "save_to_variable": "date_of_birth",
                    "expected_type": "text",
                    "validation_regex": "^\\d{4}-\\d{2}-\\d{2}$"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "That doesn't look like a valid date format. Please use YYYY-MM-DD."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_email",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        {
            "name": "ask_email",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "What is your email address? This will help us keep you updated."}
                },
                "reply_config": {
                    "save_to_variable": "email",
                    "expected_type": "email"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "That doesn't look like a valid email. Please enter a correct email address."
                }
            },
            "transitions": [
                {
                    "to_step": "ask_city",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        {
            "name": "ask_city",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Which city do you currently live in?"}
                },
                "reply_config": {"save_to_variable": "city", "expected_type": "text"},
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Sorry, I didn't get that. Please tell me which city you live in."
                }
            },
            "transitions": [
                {"to_step": "confirm_details", "condition_config": {"type": "always_true"}}
            ]
        },

        # 5. Ask the user to confirm all the details they've entered.
        {
            "name": "confirm_details",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive",
                    "interactive": {
                        "type": "button",
                        "header": {"type": "text", "text": "Confirm Your Details"},
                        "body": {
                            "text": "Great, thank you! Please review your information:\n\n*Full Name:* {{ first_name }} {{ last_name }}\n*Gender:* {{ gender|title }}\n*Marital Status:* {{ marital_status|title }}\n*Date of Birth:* {{ date_of_birth }}\n*Email:* {{ email }}\n*City:* {{ city }}\n\nDoes this look correct?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_save", "title": "Yes, Save Profile"}},
                                {"type": "reply", "reply": {"id": "restart_registration", "title": "No, Start Over"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "confirmation_choice",
                    "expected_type": "interactive_id"
                },
                "fallback_config": {
                    "action": "re_prompt", "max_retries": 1,
                    "re_prompt_message_text": "Please make a selection by tapping one of the buttons."
                }
            },
            "transitions": [
                {"to_step": "save_profile_data", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_save"}},
                {"to_step": "start_registration", "condition_config": {"type": "interactive_reply_id_equals", "value": "restart_registration"}}
            ]
        },

        # 6. Save the data to the database after confirmation.
        {
            "name": "save_profile_data",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "update_member_profile",
                        "fields_to_update": {
                            "first_name": "{{ first_name }}",
                            "last_name": "{{ last_name }}",
                            "gender": "{{ gender }}",
                            "marital_status": "{{ marital_status }}",
                            "date_of_birth": "{{ date_of_birth }}",
                            "email": "{{ email }}",
                            "city": "{{ city }}"
                        }
                    },
                    {
                        "action_type": "update_contact_field",
                        "field_path": "name",
                        "value_template": "{{ first_name }} {{ last_name }}"
                    }
                ]
            },
            "transitions": [
                {"to_step": "end_registration", "condition_config": {"type": "always_true"}}
            ]
        },

        # 7a. End the flow successfully.
        {
            "name": "end_registration",
            "type": "end_flow",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Thank you, {{ first_name }}! Your profile has been saved. Welcome to the community! 🙏"}
                }
            },
            "transitions": []
        },

        # 7b. End the flow if the user cancels.
        {
            "name": "end_flow_cancelled",
            "type": "end_flow",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Okay, no changes have been made. Type 'menu' to return to the main menu."}
                }
            },
            "transitions": []
        }
    ]
}