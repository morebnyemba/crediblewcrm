# whatsappcrm_backend/flows/definitions/registration_flow.py

"""
This flow definition collects all the necessary data to create a MemberProfile.
It uses various message types for a bSetter user experience and concludes
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
                        "body": "Welcome to our new member registration! We need to ask a few questions to get you set up.\n\nLet's start with your first name. What is your first name?"
                    }
                },
                "reply_config": {
                    "save_to_variable": "first_name",
                    "expected_type": "text"
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
                        "type": "button",
                        "body": {
                            "text": "What is your gender?"
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "male", "title": "Male"}},
                                {"type": "reply", "reply": {"id": "female", "title": "Female"}}
                            ]
                        }
                    }
                },
                "reply_config": {
                    "save_to_variable": "gender",
                    "expected_type": "interactive_id"
                }
            },
            "transitions": {
                "