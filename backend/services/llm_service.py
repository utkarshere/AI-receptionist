import os
import json
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import AsyncOpenAI
from ..utils import db_utils
from ..services import email_service

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) #type: ignore

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check if any consultants are available for a given service and start time. Use this before booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "description": "The name of the service, e.g., 'Technology', 'Sales', 'Financial', 'Legal'."},
                    "requested_datetime_str": {"type": "string", "description": "The requested date and time in 'YYYY-MM-DD HH:MM:SS' format."}
                },
                 "required": ["service_name", "requested_datetime_str"],
             }
        }
    },
     {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Books an appointment. The user's name, email, service ID, and datetime must be known.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "The user's full name."},
                    "user_email": {"type": "string", "description": "The user's email address."},
                    "appt_datetime": {"type": "string", "description": "The requested date and time in 'YYYY-MM-DD HH:MM:SS' format."},
                    "service_id": {"type": "integer", "description": "The ID of the service to book (1=Technology, 2=Sales, 3=Financial, 4=Legal)."},
                 },
                 "required": ["user_name", "user_email", "appt_datetime", "service_id"],
             }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_next_available_slot",
            "description": "If a user's requested time is unavailable, use this to find the *next* open slot.",
            "parameters": {
                "type": "object",
                 "properties": {
                    "service_name": {"type": "string", "description": "The name of the service, e.g., 'Technology'"},
                    "start_datetime_str": {"type": "string", "description": "The user's *original* requested date and time in 'YYYY-MM-DD HH:MM:SS' format."},
                 },
                 "required": ["service_name", "start_datetime_str"],
             }
        }
    },
     {
        "type": "function",
        "function": {
            "name": "get_user_appointments",
            "description": "Fetches a list of all *active* appointments for a user, based on their email. Use this before any cancel or reschedule attempt.",
            "parameters": {
                "type": "object",
                 "properties": {
                    "user_email": {"type": "string", "description": "The user's email address to search for."},
                 },
                 "required": ["user_email"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancels an active appointment using its unique ID and the user's email.",
            "parameters": {
                 "type": "object",
                 "properties": {
                     "appointment_id": {"type": "integer", "description": "The unique ID of the appointment to cancel."},
                    "user_email": {"type": "string", "description": "The user's email, for verification."},
                 },
                 "required": ["appointment_id", "user_email"],
             }
         }
     },
     {
         "type": "function",
         "function": {
             "name": "reschedule_appointment",
            "description": "Reschedules an existing appointment to a new date and time.",
            "parameters": {
                 "type": "object",
                 "properties": {
                     "appointment_id": {"type": "integer", "description": "The ID of the appointment to reschedule."},
                    "user_email": {"type": "string", "description": "The user's email, for verification."},
                    "new_appt_datetime": {"type": "string", "description": "The *new* desired date and time in 'YYYY-MM-DD HH:MM:SS' format."},
                 },
                 "required": ["appointment_id", "user_email", "new_appt_datetime"],
             }
         }
     },
     {
         "type": "function",
         "function": {
             "name": "modify_appointment_service",
             "description": "Modifies the service (e.g., from 'Technology' to 'Legal') for an existing appointment.",
            "parameters": {
                "type": "object",
                 "properties": {
                     "appointment_id": {"type": "integer", "description": "The ID of the appointment to modify."},
                    "user_email": {"type": "string", "description": "The user's email, for verification."},
                     "new_service_id": {"type": "integer", "description": "The ID of the *new* service (1=Technology, 2=Sales, 3=Financial, 4=Legal)."},
                 },
                 "required": ["appointment_id", "user_email", "new_service_id"],
            }
        }
    }
]

SYSTEM_PROMPT = f"""
You are an expert AI receptionist for a high-end consulting firm.
The current date is: {datetime.now().strftime('%Y-%m-%d %A')}.
The available services are: 1=Technology, 2=Sales, 3=Financial, 4=Legal.

Your job is to orchestrate a conversation to help a user book, cancel, reschedule, or modify appointments.

**Core Interaction Flow:**
1.  Understand the user's intent (book, check, cancel, etc.).
2.  Gather all necessary information (service, specific date/time, user name, email, appointment ID).
3.  Calculate absolute dates/times ('YYYY-MM-DD HH:MM:SS') from any relative input.
4.  **MANDATORY Confirmation Step (Before any Write Action):**
    * Before calling `book_appointment`, `reschedule_appointment`, or `modify_appointment_service`, you MUST **first** call `check_availability` for the target slot.
    * If `check_availability` returns an *empty list* (slot is unavailable), you MUST follow the failure rules in Step 6.
    * If `check_availability` returns *available consultants*, you MUST then repeat the full details (Service, Date, Time, User Name, Email) and ask for explicit confirmation ("Shall I proceed...?").
    * **CRITICAL:** When the user responds affirmatively (e.g., "Yes", "Confirm", "Book it"), your *next and only action* MUST be to call the correct tool (`book_appointment`, etc.).
    * **DO NOT** generate a final confirmation text *until* the tool has been called and has returned a successful result.
5.  If a tool is called, use its result for your final response.
6.  **Failure Handling:**
    * If a tool call returns an error string (e.g., "Booking failed: No consultants available..."), you MUST politely report this error to the user.
    * If `check_availability` fails (returns empty list) during a *booking* or *rescheduling* request, you MUST then call `find_next_available_slot` to be helpful. Propose the new time to the user.
7.  **Past Date Rules:**
    * The user can **never** book or reschedule an appointment to a date/time in the past (before {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}). Politely refuse this.
    * A user **cannot** reschedule or cancel an appointment *after* its original start time has already passed.
8.  **General Availability:** If the user asks for general availability (e.g., "What times tomorrow?"), you **MUST** ask for the specific service first. Then, use `check_availability` iteratively for standard hourly slots (10 AM, 11 AM, 12 PM, 2 PM, 3 PM, 4 PM, 5 PM) and summarize the results.
9.  **Refusal:** You **MUST NOT** answer any questions outside of this specific domain (scheduling, services). Politely refuse with a message like, "I'm sorry, I can only assist with scheduling appointments and our services."

**General Rules:**
-   Always be polite and professional.
-   Do NOT ask for information you already have from the conversation history.
"""

TERMINATION_PHRASES = [
    "thank you that's all", "thanks that's all", "no more help needed",
    "no more assistance needed", "that's it", "goodbye", "bye"
]
END_CHAT_SIGNAL = "__END_CHAT__"

async def get_llm_response_with_history(session_id: str, messages_history: list[dict]) -> str:
    if messages_history:
        last_user_message = messages_history[-1].get("content", "")
        normalized_message = last_user_message.lower().strip().replace('.', '').replace('!', '')
        if normalized_message in TERMINATION_PHRASES:
            print("LLM: Detected termination phrase.")
            return END_CHAT_SIGNAL
    else:
        return "It seems we just started. How can I help?"

    messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}] + messages_history

    MAX_TOOL_CALLS = 5
    loop_count = 0
    final_response_content = None

    while loop_count < MAX_TOOL_CALLS:
        loop_count += 1
        print(f"\nLLM: Thinking... (Loop iteration {loop_count})")

        try:
            completion = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_llm, # type: ignore
                tools=tools_schema, # type: ignore
                tool_choice="auto"
            )
        except Exception as e:
            print(f"Error in LLM Call: {e}")
            return "I'm sorry, I'm having trouble connecting to my brain right now."

        response_message = completion.choices[0].message
        response_message_dict = response_message.model_dump()
        messages_for_llm.append(response_message_dict)

        if response_message.tool_calls:
            print(f"LLM: Requesting tool call(s): {[tc.function.name for tc in response_message.tool_calls if tc.type == 'function']}")

            tool_results_for_next_turn = []
            for tool_call in response_message.tool_calls:
                tool_result_content_for_llm = None
                function_name = "unknown_function"

                if tool_call.type == "function":
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                        print(f"LLM: EXECUTING function: {function_name} with args: {function_args}")
                        tool_result_value = None
                        email_action = None
                        appointment_id_for_email = None

                        if function_name == "check_availability":
                            tool_result_value = db_utils.check_availability(**function_args)
                        elif function_name == "book_appointment":
                             tool_result_value = db_utils.book_appointment(**function_args)
                             if isinstance(tool_result_value, int):
                                 email_action = 'booked'; appointment_id_for_email = tool_result_value
                        elif function_name == "find_next_available_slot":
                            tool_result_value = db_utils.find_next_available_slot(**function_args)
                        elif function_name == "get_user_appointments":
                            tool_result_value = db_utils.get_user_appointments(**function_args)
                        elif function_name == "cancel_appointment":
                            appointment_id_for_email = function_args.get("appointment_id")
                            tool_result_value = db_utils.cancel_appointment(**function_args)
                            if tool_result_value is True: email_action = 'cancelled'
                        elif function_name == "reschedule_appointment":
                            appointment_id_for_email = function_args.get("appointment_id")
                            tool_result_value = db_utils.reschedule_appointment(**function_args)
                            if tool_result_value is True: email_action = 'rescheduled'
                        elif function_name == "modify_appointment_service":
                             appointment_id_for_email = function_args.get("appointment_id")
                             tool_result_value = db_utils.modify_appointment_service(**function_args)
                             if tool_result_value is True: email_action = 'modified'
                        else:
                             tool_result_value = f"Error: Unknown tool '{function_name}'."

                        if isinstance(tool_result_value, (str, list, dict, tuple)) or tool_result_value is None:
                             tool_result_content_for_llm = str(tool_result_value)
                        elif isinstance(tool_result_value, int) and function_name == "book_appointment":
                             tool_result_content_for_llm = f"Booking successful. New appointment ID: {tool_result_value}"
                        elif tool_result_value is True:
                             tool_result_content_for_llm = f"{function_name.replace('_', ' ').capitalize()} successful."
                        else:
                             tool_result_content_for_llm = f"Tool executed with result: {tool_result_value}"

                        print(f"LLM: Tool result: {tool_result_content_for_llm}")

                        if email_action and appointment_id_for_email:
                            print(f"LLM: Attempting to send '{email_action}' email...")
                            try:
                                user_email_for_message = function_args.get("user_email")
                                if not user_email_for_message:
                                    details = db_utils.get_booking_details(appointment_id_for_email, ignore_status=True)
                                    if details: user_email_for_message = details.get('user_email')

                                if user_email_for_message:
                                    email_sent = email_service.send_appointment_email(
                                        appointment_id=appointment_id_for_email, action=email_action
                                    )
                                    if email_sent:
                                        db_utils.mark_confirmation_sent(appointment_id_for_email)
                                        tool_result_content_for_llm += f" Confirmation email sent to {user_email_for_message}."
                                    else:
                                        tool_result_content_for_llm += " (Note: Email sending failed.)"
                                else:
                                     print("LLM: Could not find email address for confirmation.")

                            except Exception as e_email:
                                 print(f"LLM: Email Error: {e_email}")

                    except Exception as e:
                        print(f"Error executing tool '{function_name}': {e}")
                        tool_result_content_for_llm = f"An internal error occurred: {e}"

                else:
                    tool_result_content_for_llm = "Error: Unrecognized tool call type."

                tool_results_for_next_turn.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": str(tool_result_content_for_llm)
                })

            messages_for_llm.extend(tool_results_for_next_turn)
            continue

        else:
            final_response_content = response_message.content
            if final_response_content is None:
                 final_response_content = "I seem unable to respond now. Please try again."
            break

    if final_response_content:
         return final_response_content
    elif loop_count >= MAX_TOOL_CALLS:
         return "I seem to be stuck processing that. Could you please rephrase?"
    else:
         return "Something unexpected happened. Please try again."