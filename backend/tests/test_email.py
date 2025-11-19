import asyncio
from backend.services import email_service
from backend.utils import db_utils 


TEST_APPOINTMENT_ID = 5 # CHANGE THIS TO REAL ID IN DATABASE AVAILABLE
TEST_ACTION = 'booked' # 'booked', 'rescheduled', 'modified', 'cancelled'


async def run_email_test():
    print(f"--- Starting Email Test ---")
    print(f"Attempting to send '{TEST_ACTION}' email for Appointment ID: {TEST_APPOINTMENT_ID}")

    try:
        conn = db_utils.get_db_connection()
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Please ensure init_db.py has been run successfully.")
        return

    
    success = email_service.send_appointment_email(
        appointment_id=TEST_APPOINTMENT_ID,
        action=TEST_ACTION
    )

    if success:
        print("\nEmail function reported SUCCESS.")
        details = db_utils.get_booking_details(TEST_APPOINTMENT_ID, ignore_status=True)
        if details and details.get('confirmation_sent_at'):
             print(f"DB Check: Confirmation timestamp found - {details['confirmation_sent_at']}")
        else:
             print("DB Check: Confirmation timestamp NOT found or details couldn't be fetched.")

    else:
        print("\nEmail function reported FAILURE.")

    print("--- Email Test Complete ---")

if __name__ == "__main__":
   
    if not email_service.EMAIL_ADDRESS or not email_service.EMAIL_PASSWORD:
        print("ERROR: EMAIL_ADDRESS or EMAIL_PASSWORD not found in .env file.")
        print("Please ensure your .env file is correctly set up in the root directory.")
    else:
        # asyncio.run is still needed to run the async 'run_email_test' wrapper
        asyncio.run(run_email_test())