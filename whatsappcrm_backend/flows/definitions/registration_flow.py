"""
This flow definition collects all the necessary data to create or update a MemberProfile.
It uses various message types for a better user experience and concludes
by using an 'action' step to persist the data.

Changes:
- Added steps to collect more fields from the MemberProfile model:
  - secondary_phone_number
  - membership_status
  - address_line_1, state_province, country
  - baptism_date
- Reordered questions for a more logical flow.
- Made optional fields skippable by allowing a 'skip' reply.
- Updated the confirmation and save steps to include the new fields.
- Expanded the 'load_existing_profile_to_context' action for comprehensive updates.
"""

REGISTRATION_FLOW = {
    "name": "member_registration",
    "friendly_name": "New Member Registration",
    "description": "Collects information to create or update a member profile.",
    "trigger_keywords": ["register", "join", "signup"],
    "is_active": True,
    "steps": [
        # 1. Check if a profile already exists to decide whether to register or update.
        {
            "name": "check_existing_profile",
            "is_entry_point": True,
            "type": "action",
            "config": {"actions_to_run": []}, # Assumes an action here populates 'member_profile' if it exists
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
                "fallback_config": {"action": "re_prompt", "max_retries": 1, "re_prompt_message_text": "Please tap one of the buttons to continue."}
            },
            "transitions": [
                {"to_step": "load_existing_profile_to_context", "condition_config": {"type": "interactive_reply_id_equals", "value": "start_update"}},
                {"to_step": "end_flow_cancelled", "condition_config": {"type": "interactive_reply_id_equals", "value": "cancel_update"}}
            ]
        },

        # 2b. Load existing data into context for a smoother update experience
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
                    {"action_type": "set_context_variable", "variable_name": "secondary_phone_number", "value_template": "{{ member_profile.secondary_phone_number }}"},
                    {"action_type": "set_context_variable", "variable_name": "address_line_1", "value_template": "{{ member_profile.address_line_1 }}"},
                    {"action_type": "set_context_variable", "variable_name": "city", "value_template": "{{ member_profile.city }}"},
                    {"action_type": "set_context_variable", "variable_name": "state_province", "value_template": "{{ member_profile.state_province }}"},
                    {"action_type": "set_context_variable", "variable_name": "country", "value_template": "{{ member_profile.country }}"},
                    {"action_type": "set_context_variable", "variable_name": "membership_status", "value_template": "{{ member_profile.membership_status }}"},
                    {"action_type": "set_context_variable", "variable_name": "baptism_date", "value_template": "{{ member_profile.baptism_date }}"},
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
                    "text": {"body": "Welcome! To register or update your profile, I'll ask a few quick questions.\n\nLet's start with your first name."}
                },
                "reply_config": {"save_to_variable": "first_name", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "I didn't quite get that. Please enter your first name."}
            },
            "transitions": [{"to_step": "ask_last_name", "condition_config": {"type": "always_true"}}]
        },

        # --- Personal Details ---
        {
            "name": "ask_last_name",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "Great, {{ first_name }}! What is your last name?"}},
                "reply_config": {"save_to_variable": "last_name", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Sorry, I didn't catch that. Please enter your last name."}
            },
            "transitions": [{"to_step": "ask_email", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_email",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "What is your email address?"}},
                "reply_config": {"save_to_variable": "email", "expected_type": "email"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "That doesn't look like a valid email. Please enter a correct email address."}
            },
            "transitions": [{"to_step": "ask_dob", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_dob",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "What is your date of birth?\n\nPlease use the format YYYY-MM-DD (e.g., 1990-05-21)."}},
                "reply_config": {"save_to_variable": "date_of_birth", "expected_type": "text", "validation_regex": "^\\d{4}-\\d{2}-\\d{2}$"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "That doesn't look like a valid date format. Please use YYYY-MM-DD."}
            },
            "transitions": [{"to_step": "ask_gender", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_gender",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive", "interactive": {"type": "list", "header": {"type": "text", "text": "Gender Selection"}, "body": {"text": "Please select your gender."}, "action": {"button": "Select Gender", "sections": [{"title": "Options", "rows": [{"id": "male", "title": "Male"}, {"id": "female", "title": "Female"}, {"id": "other", "title": "Other"}, {"id": "prefer_not_to_say", "title": "Prefer not to say"}]}]}}
                },
                "reply_config": {"save_to_variable": "gender", "expected_type": "interactive_id"},
                "fallback_config": {"action": "re_prompt", "max_retries": 1, "re_prompt_message_text": "Please make a selection from the list to continue."}
            },
            "transitions": [{"to_step": "ask_marital_status", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_marital_status",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive", "interactive": {"type": "list", "header": {"type": "text", "text": "Marital Status"}, "body": {"text": "What is your marital status?"}, "action": {"button": "Select Status", "sections": [{"title": "Options", "rows": [{"id": "single", "title": "Single"}, {"id": "married", "title": "Married"}, {"id": "divorced", "title": "Divorced"}, {"id": "widowed", "title": "Widowed"}]}]}}
                },
                "reply_config": {"save_to_variable": "marital_status", "expected_type": "interactive_id"},
                "fallback_config": {"action": "re_prompt", "max_retries": 1, "re_prompt_message_text": "Please make a selection from the list to continue."}
            },
            "transitions": [{"to_step": "ask_membership_status", "condition_config": {"type": "always_true"}}]
        },

        # --- Church Details ---
        {
            "name": "ask_membership_status",
            "type": "question",
            "config": {
                "message_config": {
                    "message_type": "interactive", "interactive": {"type": "list", "header": {"type": "text", "text": "Membership Status"}, "body": {"text": "Please select your current membership status."}, "action": {"button": "Select Status", "sections": [{"title": "Options", "rows": [{"id": "visitor", "title": "Visitor"}, {"id": "new_convert", "title": "New Convert"}, {"id": "member", "title": "Member"}, {"id": "leader", "title": "Leader"}, {"id": "inactive", "title": "Inactive"}, {"id": "other", "title": "Other"}]}]}}
                },
                "reply_config": {"save_to_variable": "membership_status", "expected_type": "interactive_id"},
                "fallback_config": {"action": "re_prompt", "max_retries": 1, "re_prompt_message_text": "Please make a selection from the list to continue."}
            },
            "transitions": [{"to_step": "ask_address_line_1", "condition_config": {"type": "always_true"}}]
        },

        # --- Location Details ---
        {
            "name": "ask_address_line_1",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "Now for your address. What is the first line of your address (e.g., street and house number)?"}},
                "reply_config": {"save_to_variable": "address_line_1", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Please enter your street address."}
            },
            "transitions": [{"to_step": "ask_city", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_city",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "Which city do you live in?"}},
                "reply_config": {"save_to_variable": "city", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Please tell me which city you live in."}
            },
            "transitions": [{"to_step": "ask_state_province", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_state_province",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "And which state or province?"}},
                "reply_config": {"save_to_variable": "state_province", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Please enter your state or province."}
            },
            "transitions": [{"to_step": "ask_country", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_country",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "Finally, which country do you live in?"}},
                "reply_config": {"save_to_variable": "country", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Please enter your country."}
            },
            "transitions": [{"to_step": "ask_secondary_phone", "condition_config": {"type": "always_true"}}]
        },

        # --- Optional Details ---
        {
            "name": "ask_secondary_phone",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "What's an alternative phone number? (Optional)\n\nType 'skip' if you don't want to provide one."}},
                "reply_config": {"save_to_variable": "secondary_phone_number", "expected_type": "text"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Please enter a valid phone number or type 'skip'."}
            },
            "transitions": [{"to_step": "ask_baptism_date", "condition_config": {"type": "always_true"}}]
        },
        {
            "name": "ask_baptism_date",
            "type": "question",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "When were you baptized? (Optional)\n\nPlease use YYYY-MM-DD format, or type 'skip'."}},
                "reply_config": {"save_to_variable": "baptism_date", "expected_type": "text", "validation_regex": "^(\\d{4}-\\d{2}-\\d{2}|[Ss][Kk][Ii][Pp])$"},
                "fallback_config": {"action": "re_prompt", "max_retries": 2, "re_prompt_message_text": "Invalid format. Please use YYYY-MM-DD or type 'skip'."}
            },
            "transitions": [{"to_step": "confirm_details", "condition_config": {"type": "always_true"}}]
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
                            "text": (
                                "Great, thank you! Please review your information:\n\n"
                                "*Name:* {{ first_name }} {{ last_name }}\n"
                                "*Email:* {{ email }}\n"
                                "*DOB:* {{ date_of_birth }}\n"
                                "*Gender:* {{ gender|title }}\n"
                                "*Marital Status:* {{ marital_status|title }}\n"
                                "*Membership:* {{ membership_status|replace('_', ' ')|title }}\n\n"
                                "*Address:* {{ address_line_1 }}, {{ city }}, {{ state_province }}, {{ country }}\n\n"
                                "*Secondary Phone:* {% if secondary_phone_number and secondary_phone_number|lower != 'skip' %}{{ secondary_phone_number }}{% else %}Not Provided{% endif %}\n"
                                "*Baptism Date:* {% if baptism_date and baptism_date|lower != 'skip' %}{{ baptism_date }}{% else %}Not Provided{% endif %}\n\n"
                                "Does this look correct?"
                            )
                        },
                        "action": {
                            "buttons": [
                                {"type": "reply", "reply": {"id": "confirm_save", "title": "Yes, Save Profile"}},
                                {"type": "reply", "reply": {"id": "restart_registration", "title": "No, Start Over"}}
                            ]
                        }
                    }
                },
                "reply_config": {"save_to_variable": "confirmation_choice", "expected_type": "interactive_id"},
                "fallback_config": {"action": "re_prompt", "max_retries": 1, "re_prompt_message_text": "Please tap one of the buttons."}
            },
            "transitions": [
                {"to_step": "save_profile_data", "condition_config": {"type": "interactive_reply_id_equals", "value": "confirm_save"}},
                {"to_step": "start_registration", "condition_config": {"type": "interactive_reply_id_equals", "value": "restart_registration"}}
            ]
        },

        # 6. Save the data to the database after confirmation.
        # NOTE: The 'update_member_profile' action must be able to handle 'skip' values for optional fields, converting them to None.
        {
            "name": "save_profile_data",
            "type": "action",
            "config": {
                "actions_to_run": [
                    {
                        "action_type": "update_member_profile",
                        "fields_to_update": {
                            "first_name": "{{ first_name }}", "last_name": "{{ last_name }}",
                            "email": "{{ email }}", "date_of_birth": "{{ date_of_birth }}",
                            "gender": "{{ gender }}", "marital_status": "{{ marital_status }}",
                            "membership_status": "{{ membership_status }}",
                            "address_line_1": "{{ address_line_1 }}", "city": "{{ city }}",
                            "state_province": "{{ state_province }}", "country": "{{ country }}",
                            "secondary_phone_number": "{{ secondary_phone_number }}",
                            "baptism_date": "{{ baptism_date }}"
                        }
                    },
                    {"action_type": "update_contact_field", "field_path": "name", "value_template": "{{ first_name }} {{ last_name }}"}
                ]
            },
            "transitions": [{"to_step": "end_registration", "condition_config": {"type": "always_true"}}]
        },

        # 7a. End the flow successfully.
        {
            "name": "end_registration",
            "type": "end_flow",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "Thank you, {{ first_name }}! Your profile has been saved. Welcome to the community! 🙏"}}
            },
            "transitions": []
        },

        # 7b. End the flow if the user cancels.
        {
            "name": "end_flow_cancelled",
            "type": "end_flow",
            "config": {
                "message_config": {"message_type": "text", "text": {"body": "Okay, no changes have been made. Type 'menu' to see other options."}}
            },
            "transitions": []
        }
    ]
}