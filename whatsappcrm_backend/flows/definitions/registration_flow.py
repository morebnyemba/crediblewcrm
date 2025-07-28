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
    "initial_step": "start_registration",
    "steps": {
        "start_registration": {
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
                    "max_retries": 2,
                    "re_prompt_message": "Sorry, I didn't catch that. Please enter your first name.",
                    "on_max_retries_transition_to": "end_registration_failed"
                }
            },
            "transitions": {
                "next": "ask_last_name"
            }
        },
        "ask_last_name": {
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
                    "max_retries": 2,
                    "re_prompt_message": "Sorry, I didn't catch that. Please enter your last name.",
                    "on_max_retries_transition_to": "end_registration_failed"
                }
            },
            "transitions": {
                "next": "ask_gender"
            }
        },
        "ask_gender": {
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
                    "max_retries": 1,
                    "re_prompt_message": "Please make a selection from the list to continue.",
                    "on_max_retries_transition_to": "end_registration_failed"
                }
            },
            "transitions": {
                "next": "ask_marital_status"
            }
        },
        "ask_marital_status": {
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
                    "max_retries": 1,
                    "re_prompt_message": "Please make a selection from the list to continue.",
                    "on_max_retries_transition_to": "end_registration_failed"
                }
            },
            "transitions": {
                "next": "ask_dob"
            }
        },
        "ask_dob": {
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
                    "max_retries": 2,
                    "re_prompt_message": "That doesn't look like a valid date format. Please use YYYY-MM-DD.",
                    "on_max_retries_transition_to": "end_registration_failed"
                }
            },
            "transitions": {
                "next": "ask_email"
            }
        },
        "ask_email": {
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
                    "max_retries": 2,
                    "re_prompt_message": "That doesn't look like a valid email. Please enter a correct email address.",
                    "on_max_retries_transition_to": "end_registration_failed"
                }
            },
            "transitions": {
                "next": "ask_city"
            }
        },
        "ask_city": {
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Which city do you currently live in?"}
                },
                "reply_config": {"save_to_variable": "city", "expected_type": "text"},
                "fallback_config": {
                    "max_retries": 2,
                    "re_prompt_message": "Sorry, I didn't get that. Please tell me which city you live in.",
                    "on_max_retries_transition_to": "end_registration_failed"
                }
            },
            "transitions": {
                "next": "save_profile_data"
            }
        },
        "save_profile_data": {
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
            "transitions": {
                "next": "end_registration"
            }
        },
        "end_registration": {
            "type": "end_flow",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Thank you, {{ context.first_name }}! Your profile has been updated. Welcome to the community! 🙏"}
                }
            }
        },
        "end_registration_failed": {
            "type": "end_flow",
            "config": {
                "message_config": {
                    "message_type": "text",
                    "text": {"body": "Sorry, we couldn't complete your registration right now. Please type 'register' to try again later."}
                }
            }
        }
    }
}