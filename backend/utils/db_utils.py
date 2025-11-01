import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any


DIR_NAME = 'data'
DB_NAME = 'consulting.db'
DB_PATH = os.path.join(DIR_NAME, DB_NAME)   

def get_db_connection():
    '''
    Establishes and returns a database connection.
    Configures the connection to return rows as dictionary-like objects.
    '''

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row
    return conn

def create_session_if_not_exists(session_id: str):
    """
    Ensures a row exists in session_state for the given session_id.
    This prevents errors if trying to update a session which does not exist.
    """
    conn = get_db_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO session_state (session_id) VALUES (?)", (session_id,))
        conn.commit()

    except Exception as e:
        print(f"Error creating session: {e}")
    finally:
        conn.close()



def update_session_state(session_id: str, data: dict):
    """
    Updates the session_state table with new metadata. data is a dictionary structure containing data related to user and requested service.
    
    """

    if not data:
        return
    
    conn = get_db_connection()

    try:
        set_clauses = [f'{key} = ?' for key in data.keys()]
        values = list(data.values())
        values.append(session_id)

        query = f"""
        UPDATE session_state
        SET {', '.join(set_clauses)}, last_updated = CURRENT_TIMESTAMP
        WHERE session_id = ?
        """

        conn.execute(query, tuple(values))
        conn.commit()
    except Exception as e:
        print(f"Error updating session state: {e}")
    finally:
        conn.close()


def get_session_state(session_id: str):

    """
    Retrieves the full metadata state for a given session. Returns dictionary like row object or none.

    """
    conn = get_db_connection()

    try:
        cursor = conn.execute(
            "SELECT * FROM session_state WHERE session_id = ?",
            (session_id,)
        )
        return cursor.fetchone()
    except Exception as e:
        print(f"Error getting session state: {e}")
        return None
    finally:
        conn.close()

def add_conversation_message(session_id: str, role: str, message: str):
    """
    Logs a single message (from 'user' or 'ai') to the conversation history.

    """

    conn = get_db_connection()
    try:
        conn.execute(
        "INSERT INTO conversation_history (session_id, role, message_text) VALUES (?, ?, ?)", (session_id, role, message)
        )
        conn.commit()
        
    except Exception as e:
        print(f"Error adding conversation message: {e}")

    finally:
        conn.close()

def get_conversation_history(session_id: str, limit: int = 10):
    """
    Gets the last 'limit' messages for a session to provide context to the LLM.
    Returns a list of dictionary-like row objects.
    """

    conn = get_db_connection()

    try:
        cursor = conn.execute(
            """
            SELECT role, message_text FROM conversation_history
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (session_id, limit)
        )
        history =  cursor.fetchall()
        return list(reversed(history))
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []
    finally:
        conn.close()

def check_availability(service_name: str, requested_datetime_str: str):
    """
    Check which consultants are available for a 60 minute slot starting at the requested datetime.

    requested_datetime_str format: 'YYYY-MM-DD HH:MM:SS'

    Returns: a list of available consultant dictionaries
    """

    try:
        dt = datetime.fromisoformat(requested_datetime_str)
        day_of_week = dt.weekday()
        time_str = dt.strftime('%H:%M')

        conn = get_db_connection()
        cursor = conn.execute(
            """
            SELECT c.consultant_id, c.name
            FROM consultants c
            JOIN services s ON c.service_id = s.service_id 
            JOIN consultant_availability ca ON c.consultant_id = ca.consultant_id
            WHERE
                -- 1. Does a consultant offer this service?
                s.service_name = ?

                -- 2. Does consultant work on this day?
                AND ca.day_of_week = ?

                -- 3. Is the START time within a valid work block?
                AND ? >= ca.start_time

                -- 4. Does the 60-min END time ALSO fall within the same block?
                AND ? <= time(ca.end_time, '-60 minutes')

                -- 5. Does an appointment already exist that overlaps this time?
                AND c.consultant_id NOT IN (
                    SELECT consultant_id
                    FROM appointments
                    WHERE 
                        status = 'booked'
                        -- Check for any booking starting 59 mins before or after
                        AND appointment_datetime BETWEEN datetime(?, '-59 minutes') AND datetime(?, '+59 minutes')
                )
            """,
            (
                service_name,
                day_of_week,
                time_str,
                time_str,
                requested_datetime_str,
                requested_datetime_str
            )
        )

        available_consultants = cursor.fetchall()
        return [dict(row) for row in available_consultants]
    
    except Exception as e:
        print(f"Error checking availability: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def book_appointment(user_name: str, user_email: str, appt_datetime: str, service_id: int):
    """
    Books an appointment.
    If a 'cancelled' slot exists for the same time, it re-books it (UPDATE).
    Otherwise, it creates a new one (INSERT).
    """
    
    conn = get_db_connection()
    
    try:
        
        service_row = conn.execute("SELECT service_name FROM services WHERE service_id = ?", (service_id,)).fetchone()
        if not service_row:
            print(f"Booking failed: No service found with ID {service_id}.")
            return None
        
        service_name = service_row['service_name']
        available_consultants = check_availability(service_name, appt_datetime)
        
        if not available_consultants:
            print(f"Booking failed: No consultants available for {service_name} at {appt_datetime}.")
            return f"Booking failed: No consultants available for {service_name} at {appt_datetime}."

        
        assigned_consultant = available_consultants[0]
        assigned_consultant_id = assigned_consultant['consultant_id']
        
      
        cursor = conn.execute(
            """
            SELECT appointment_id FROM appointments
            WHERE consultant_id = ? AND appointment_datetime = ? AND status = 'cancelled'
            """,
            (assigned_consultant_id, appt_datetime)
        )
        existing_cancelled_slot = cursor.fetchone()
        
        if existing_cancelled_slot:
            
            print(f"Re-booking existing cancelled slot. ID: {existing_cancelled_slot['appointment_id']}")
            conn.execute(
                """
                UPDATE appointments
                SET user_name = ?, user_email = ?, service_id = ?, status = 'booked'
                WHERE appointment_id = ?
                """,
                (user_name, user_email, service_id, existing_cancelled_slot['appointment_id'])
            )
            conn.commit()
            return existing_cancelled_slot['appointment_id']
            
        else:
            
            print(f"Booking new slot for consultant {assigned_consultant_id}...")
            cursor = conn.execute(
                """
                INSERT INTO appointments (user_name, user_email, appointment_datetime, consultant_id, service_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_name, user_email, appt_datetime, assigned_consultant_id, service_id)
            )
            conn.commit()
            return cursor.lastrowid

    except sqlite3.IntegrityError as e:
        print(f"Booking failed (IntegrityError) : {e}")
        conn.rollback()
        return "Booking failed: This slot is already booked."
    except Exception as e:
        print(f"Error booking appointment: {e}")
        conn.rollback()
        return f"An unexpected error occurred: {e}"
    finally:
        if conn:
            conn.close()

def get_user_appointments(user_email:str):
    
    """
    Fetches all 'booked' appointments for a given user email.
    Used for cancellation or rescheduling.

    """
    conn = get_db_connection()

    try:
        cursor = conn.execute(
            """
            SELECT
                a.appointment_id,
                a.appointment_datetime,
                c.name as consultant_name,
                s.service_name
            FROM appointments a
            JOIN consultants c ON a.consultant_id = c.consultant_id
            JOIN services s ON a.service_id = s.service_id
            WHERE a.user_email = ? AND a.status = 'booked'
            ORDER BY a.appointment_datetime""", (user_email,)
        )
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching user appointments: {e}")
        return []
    finally:
        conn.close()

def cancel_appointment(appointment_id: int, user_email: str):
    """
    Cancels an appointment by setting its status to 'cancelled'
    Checks that the email matches the appointment for security.
    Returns True on success, False on failure.
    """
    conn = get_db_connection()
    
    try: 

        cursor = conn.execute(
            """
            UPDATE appointments
            SET status = 'cancelled'
            WHERE appointment_id = ? and user_email = ? and status = 'booked'
            """,
            (appointment_id, user_email)
        )
        conn.commit()
        return cursor.rowcount > 0
    
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        return False
    finally:
        conn.close()

def modify_appointment_service(appointment_id: int, user_email: str, new_service_id: int):
    conn = get_db_connection()
    try:
        current_appt = conn.execute(
            "SELECT appointment_datetime, service_id FROM appointments WHERE appointment_id = ? AND user_email = ? AND status = 'booked'",
            (appointment_id, user_email)
        ).fetchone()
        
        if not current_appt:
            return "Modify failed: No active appointment found for that ID and email."
        
        if current_appt['service_id'] == new_service_id:
             return "Modify failed: This appointment is already for that service."
             
        appt_datetime = current_appt['appointment_datetime']
        
        new_service_name_row = conn.execute("SELECT service_name FROM services WHERE service_id = ?", (new_service_id,)).fetchone()
        if not new_service_name_row:
            return "Modify failed: Invalid new service ID."
        
        new_service_name = new_service_name_row['service_name']
        available_consultants = check_availability(new_service_name, appt_datetime)
        
        if not available_consultants:
            return f"Modify failed: No consultants available for {new_service_name} at {appt_datetime}."
            
        new_consultant_id = available_consultants[0]['consultant_id']
        
        cursor = conn.execute(
            """
            UPDATE appointments
            SET service_id = ?, consultant_id = ?
            WHERE appointment_id = ? AND user_email = ?
            """,
            (new_service_id, new_consultant_id, appointment_id, user_email)
        )
        
        conn.commit()
        return True
        
    except sqlite3.IntegrityError:
        conn.rollback()
        return "Modify failed: The new slot is already booked."
    except Exception as e:
        print(f"Error modifying appointment: {e}")
        conn.rollback()
        return f"An internal error occurred: {e}"
    finally:
        if conn:
            conn.close()

def reschedule_appointment(appointment_id: int, user_email: str, new_appt_datetime: str):
    conn = get_db_connection()
    try:
        current_appt = conn.execute(
            "SELECT service_id FROM appointments WHERE appointment_id = ? AND user_email = ? AND status = 'booked'",
            (appointment_id, user_email)
        ).fetchone()
        
        if not current_appt:
            return "Reschedule failed: No active appointment found for that ID and email."
        
        service_id = current_appt['service_id']
        service_name = conn.execute("SELECT service_name FROM services WHERE service_id = ?", (service_id,)).fetchone()['service_name']
        
        available_consultants = check_availability(service_name, new_appt_datetime)
        
        if not available_consultants:
            return f"Reschedule failed: No consultants available for {service_name} at {new_appt_datetime}."
            
        new_consultant_id = available_consultants[0]['consultant_id']

        cursor = conn.execute(
            """
            UPDATE appointments
            SET appointment_datetime = ?, consultant_id = ?
            WHERE appointment_id = ? AND user_email = ?
            """,
            (new_appt_datetime, new_consultant_id, appointment_id, user_email)
        )

        conn.commit()
        return True
        
    except sqlite3.IntegrityError:
        conn.rollback()
        return "Reschedule failed: The new slot is already booked."
    except Exception as e:
        print(f"Error rescheduling appointment: {e}")
        conn.rollback()
        return f"An internal error occurred: {e}"
    finally:
        if conn:
            conn.close()

def get_booking_details(appointment_id:int, ignore_status=False):
    
    """
    Fetches details for a single appointment.
    If ignore_status is True, fetches regardless of status (for email confirmation).
    Otherwise, only fetches 'booked' appointments.
    """


    conn = get_db_connection()
    try:
        where_clause = "WHERE a.appointment_id = ?"
        params : list[Any] = [appointment_id]
        if not ignore_status:
            where_clause += "AND a.status = ?"
            params.append('booked')
        query = f"""
            SELECT
                a.user_name, a.user_email, a.appointment_datetime,
                c.name AS consultant_name, c.email AS consultant_email,
                s.service_name
            FROM appointments a
            JOIN consultants c ON a.consultant_id = c.consultant_id
            JOIn services s ON a.service_id = s.service_id
            {where_clause}
            """
        cursor = conn.execute(query, tuple(params))
        result = cursor.fetchone()
        return dict(result) if result else None
    except Exception as e:
        print(f"Error getting booking details: {e}")
        return None
    finally:
        conn.close()

from datetime import datetime, timedelta # Make sure timedelta is imported

def find_next_available_slot(service_name: str, start_datetime_str: str):
    """
    Searches for the next available 60-minute slot for a given service,
    starting from the requested datetime.
    
    Rounds up to the next full hour if a non-hourly time is given.
    
    Searches in 60-minute increments for up to 7 days.
    
    Returns:
        A tuple (found_datetime_str, consultant_dict) or (None, None)
    """
    try:
        current_time = datetime.fromisoformat(start_datetime_str)
        
        
        if current_time.minute > 0 or current_time.second > 0 or current_time.microsecond > 0:
            print(f"Rounding up from {current_time} to the next hour.")
            
            current_time = (current_time + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        
            
        search_limit = 168 # 7 days * 24 hours
        
        for _ in range(search_limit):
            
            
            available_consultants = check_availability(service_name, current_time.isoformat(sep=' '))
            
            if available_consultants:
                
                found_consultant = available_consultants[0]
                found_datetime_str = current_time.isoformat(sep=' ')
                print(f"Found next slot: {found_datetime_str} with {found_consultant['name']}")
                return found_datetime_str, found_consultant

            
            current_time += timedelta(minutes=60)
            
        
        print("Search limit reached, no slots found within 7 days.")
        return None, None
        
    except Exception as e:
        print(f"Error finding next slot: {e}")
        return None, None
    
def mark_confirmation_sent(appointment_id: int):
    """Updates the appointment record to show the confirmation email was sent."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE appointments SET confirmation_sent_at = ? WHERE appointment_id = ?",
            (datetime.now(), appointment_id)
        )
        conn.commit()
        print(f"Marked confirmation sent for appointment ID: {appointment_id}")
    except Exception as e:
        print(f"Error marking confirmation sent: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

def get_all_services():
    """Fetches a list of all available services."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT service_id, service_name, description FROM services ORDER BY service_name")
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting all services: {e}")
        return [] 
    finally:
        if conn:
            conn.close()

def get_consultants_by_service(service_name: str):
    """Fetches all consultants associated with a specific service name."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            SELECT c.consultant_id, c.name, c.email
            FROM consultants c
            JOIN services s ON c.service_id = s.service_id
            WHERE s.service_name = ?
            ORDER BY c.name
            """,
            (service_name,)
        )
        # Convert list of Row objects to a list of standard dicts
        return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting consultants by service: {e}")
        return [] # Return empty list on error
    finally:
        if conn:
            conn.close()