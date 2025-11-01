import asyncio
from backend.services import email_service
from backend.utils import db_utils # Needed to fetch details

# --- CONFIGURE YOUR TEST ---
# Replace with a REAL appointment ID from your database
TEST_APPOINTMENT_ID = 5 # <<< CHANGE THIS
TEST_ACTION = 'booked' # Try 'booked', 'rescheduled', 'modified', 'cancelled'
# ---

async def run_email_test():
    print(f"--- Starting Email Test ---")
    print(f"Attempting to send '{TEST_ACTION}' email for Appointment ID: {TEST_APPOINTMENT_ID}")

    # Ensure database exists (optional sanity check)
    try:
        conn = db_utils.get_db_connection()
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Please ensure init_db.py has been run successfully.")
        return

    # Call the email service function
    success = await email_service.send_appointment_email(
        appointment_id=TEST_APPOINTMENT_ID,
        action=TEST_ACTION
    )

    if success:
        print("\nEmail function reported SUCCESS.")
        # Verify if it was marked in the DB (optional)
        # You might need to adjust get_booking_details to see the confirmation_sent_at
        details = db_utils.get_booking_details(TEST_APPOINTMENT_ID, ignore_status=True)
        if details and details.get('confirmation_sent_at'):
             print(f"DB Check: Confirmation timestamp found - {details['confirmation_sent_at']}")
        else:
             print("DB Check: Confirmation timestamp NOT found or details couldn't be fetched.")

    else:
        print("\nEmail function reported FAILURE.")

    print("--- Email Test Complete ---")

if __name__ == "__main__":
    # Check if email credentials are set (basic check)
    if not email_service.EMAIL_ADDRESS or not email_service.EMAIL_PASSWORD:
        print("ERROR: EMAIL_ADDRESS or EMAIL_PASSWORD not found in .env file.")
        print("Please ensure your .env file is correctly set up in the root directory.")
    else:
        asyncio.run(run_email_test())