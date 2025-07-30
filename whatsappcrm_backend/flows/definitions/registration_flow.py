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
        {
            "name": "start_registration",
            "is_entry_point": True,
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Welcome! To register you as a new member, I just need to ask a few quick questions.\n\nLet's start with your first name."
                    }
                },
                "reply_config": {
                    "save_to_variable": "first_name",
                    "expected_type": "text"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Sorry, I didn't catch that. Please enter your first name.",
                    "fallback_message_text": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."
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
        {
            "name": "ask_last_name",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {
                        "body": "Great, {{ context.first_name }}! What is your last name?"
                    }
                },
                "reply_config": {
                    "save_to_variable": "last_name",
                    "expected_type": "text"
                },
                "fallback_config": {
                    "action": "re_prompt",
                    "max_retries": 2,
                    "re_prompt_message_text": "Sorry, I didn't catch that. Please enter your last name.",
                    "fallback_message_text": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."
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
                    "re_prompt_message_text": "Please make a selection from the list to continue.",
                    "fallback_message_text": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."
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
                    "re_prompt_message_text": "Please make a selection from the list to continue.",
                    "fallback_message_text": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."
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
                    "re_prompt_message_text": "That doesn't look like a valid date format. Please use YYYY-MM-DD.",
                    "fallback_message_text": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."
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
                    "re_prompt_message_text": "That doesn't look like a valid email. Please enter a correct email address.",
                    "fallback_message_text": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."
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
                    "re_prompt_message_text": "Sorry, I didn't get that. Please tell me which city you live in.",
                    "fallback_message_text": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."
                }
            },
            "transitions": [
                {
                    "to_step": "save_profile_data",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        {
            "name": "save_profile_data",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "update_member_profile",
                        "fields_to_update": {
                            "first_name": "{{ context.first_name }}",
                            "last_name": "{{ context.last_name }}",
                            "gender": "{{ context.gender }}",
                            "marital_status": "{{ context.marital_status }}",
                            "date_of_birth": "{{ context.date_of_birth }}",
                            "email": "{{ context.email }}",
                            "city": "{{ context.city }}",
                            "last_updated_from_conversation": "{{ now }}"
                        }
                    }
                ]
            },
            "transitions": [
                {
                    "to_step": "end_registration",
                    "priority": 10,
                    "condition_config": {
                        "type": "always_true"
                    }
                }
            ]
        },
        {
            "name": "end_registration",
            "type": "end_flow",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Thank you, {{ context.first_name }}! Your profile has been updated. Welcome to the community! 🙏"}
                }
            },
            "transitions": []
        },
        {
            "name": "end_registration_failed",
            "type": "end_flow",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."}
                }
            },
            "transitions": []
        }
    ]
}