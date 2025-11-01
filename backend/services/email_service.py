import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from ..utils import db_utils

load_dotenv()

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_appointment_email(appointment_id: int, action: str)->bool:
    
    """
    Sends an email notification for an appointment session.
    - action: 'booked', 'rescheduled', 'modified', 'cancelled'
    Returns True on success, False on failure.
    """

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("Email Error: Sender email address not configured.")
        return False
    
    booking_details = db_utils.get_booking_details(appointment_id, ignore_status=True)

    if not booking_details:
        print(f"Email error: Could not fetch details for appointment ID {appointment_id}.")
        return False
    user_email = booking_details.get("user_email")

    if not user_email:
        print(f"Email error: User email missing for appointment ID: {appointment_id}.")
        return False
    

    subject = ""
    body = ""
    user_name = booking_details.get("user_name", "Client")

    if action == "booked":
        subject = f"Appointment Confirmed: {booking_details.get('service_name')} Consultation."
        body = f"""
Dear {user_name},
This email confirms your new appointment:

Service: {booking_details.get('service_name')}
Consultant: {booking_details.get('consultant_name')}
Date and Time: {booking_details.get('appointment_datetime')}
Appointment ID: {appointment_id}

We look forward to speaking with you. If you have any further questions or feedback, kindly email us at {EMAIL_ADDRESS}
Sincerely,
The Consulting Firm AI Assistant
"""
    elif action == "rescheduled":
        subject = f"Appointment Rescheduled: {booking_details.get('service_name')} Consultation."
        body = f"""
Dear {user_name},
This email confirms your appointment has been rescheduled.

New Details:
Service: {booking_details.get("service_name")}
Consultant: {booking_details.get("consultant_name")}
Date and Time: {booking_details.get("appointment_datetime")}
Appointment ID: {appointment_id}

We look forward to speaking with you. If you have any further questions or feedback, kindly email us at {EMAIL_ADDRESS}
Sincerely,
The Consulting Firm AI Assistant
"""
    elif action == "modified":
        subject = f"Appointment Modified: {booking_details.get('service_name')} Consultation."
        body = f"""
Dear {user_name},
This email confirms the modification of your appointment.

Updated Details:
Service: {booking_details.get("service_name")}
Consultant: {booking_details.get("consultant_name")}
Date and Time: {booking_details.get("appointment_datetime")}
Appointment ID: {appointment_id}

We look forward to speaking with you. If you have any further questions or feedback, kindly email us at {EMAIL_ADDRESS}
Sincerely,
The Consulting Firm AI Assistant
"""
    elif action == 'cancelled':
        subject = f"Appointment Cancelled"
        body = f"""
Dear {user_name},

This email confirms that your appointment (ID: {appointment_id}) has been cancelled as requested.

If this was a mistake, or if you wish to book a new appointment, please contact us again.

Sincerely,
The Consulting Firm AI Assistant
"""
    else:
        print(f"Email error: Unknown action '{action}'.")
        return False
    
    print(f"--- Preparing Email ({action.upper()}) ---")
    print(f"To: {user_email}")
    print(f"Subject: {subject}")

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = user_email
        
        msg.set_content(body)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print(f"Email ({action}) sent successfully to {user_email}!")
        return True
    except Exception as e:
        print(f"Email Error: Failed to send {action} email - {e}")
        return False


        
