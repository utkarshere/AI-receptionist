import sqlite3
import os

SCRIPT_PATH = os.path.abspath(__file__)

SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))


DB_DIR = os.path.join(PROJECT_ROOT, 'data')
DB_NAME = 'consulting.db'
DB_PATH = os.path.join(DB_DIR, DB_NAME)


def initialize_database():
    '''Initializes and populates consulting database with seed data regarding the consultants'''

    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Database created successfully at data/consulting.db.")


    

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS services (
                   service_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   service_name TEXT NOT NULL UNIQUE,
                   description TEXT
                   )
                   ''')
    print("Created 'services' table.")

    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS consultants (
                   consultant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL,
                   email TEXT NOT NULL UNIQUE,
                   service_id INTEGER NOT NULL,
                   FOREIGN KEY (service_id) REFERENCES services (service_id)
                   )
                   ''')
    print("Created 'consultants' table.")

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS consultant_availability (
                   availability_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   consultant_id INTEGER NOT NULL,
                   day_of_week INTEGER NOT NULL, --0=Monday, 1=Tuesday, ..., 6=Sunday
                   start_time TEXT NOT NULL, --'HH:MM' format (e.g. '11:00')
                   end_time TEXT NOT NULL, -- (e.g. '17:00')
                   FOREIGN KEY (consultant_id) REFERENCES consultants (consultant_id)
                   )
                   ''')
    print("Created 'consultant_availability' table.")


    cursor.execute('''
                 CREATE TABLE IF NOT EXISTS appointments(
                 appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_name TEXT NOT NULL,
                 user_email TEXT NOT NULL,
                 appointment_datetime TEXT NOT NULL,
                 consultant_id INTEGER NOT NULL,
                 service_id INTEGER NOT NULL,
                 status TEXT NOT NULL DEFAULT 'booked',
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 confirmation_sent_at TIMESTAMP NULL,
                 FOREIGN KEY (consultant_id) REFERENCES consultants (consultant_id),
                 FOREIGN KEY (service_id) REFERENCES services (service_id)
                 )
                 ''')
    print("Created 'appointments' table.")

    cursor.execute('''
    CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_booked_appointment
    ON appointments (consultant_id, appointment_datetime)
    WHERE status = 'booked'
    ''')
    print("Created 'unique booked appointments' index.")

    
    cursor.execute('''CREATE TABLE IF NOT EXISTS conversation_history(
                   message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   session_id TEXT NOT NULL,
                   role TEXT NOT NULL, --'user' or 'ai
                   message_text TEXT NOT NULL,
                   timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   )
                   ''')
    print("Created 'conversation_history' table.")

    cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_state(
                   session_id TEXT PRIMARY KEY,
                   user_name TEXT,
                   user_email TEXT,
                   requested_service_id INTEGER,
                   requested_consultant_id INTEGER,
                   requested_datetime TEXT,
                   last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (requested_service_id) REFERENCES services (service_id),
                   FOREIGN KEY (requested_consultant_id) REFERENCES consultants (consultant_id)
                   )
                   ''')
    print("Created 'session_state' table.")

    try:
        services = [('Technology', 'Consulting on cloud, AI and software implementation.'),
                    ('Sales', 'Consulting on sales strategy, CRM and team training.'),
                    ('Financial', 'Consulting on financial planning, investment, and risk assessment.'),
                    ('Legal', 'Consulting on corporate law, compliance, and contract review.')
                    ]
        cursor.executemany("INSERT INTO services(service_name, description) VALUES (?, ?)", services)
        conn.commit()

        consultants = [('Josh Matthews', 'josh111@consult.com', 1),
                       ('James Johnson', 'johson123@consult.com', 2),
                       ('Chris Gates', 'gateschris@consult.com', 3),
                       ('David Kim', 'david121@consult.com', 4),
                       ('Sarah Jones', 'sarah234@consult.com', 2),
                       ('Christina Jaymes', 'christina121@consult.com', 3),
                       ('Emilie Johnson', 'emilie111@consult.com', 1),
                       ('Amanda Baldwin', 'amanda101@consult.com', 4)
                       ]
        
        cursor.executemany("INSERT INTO consultants(name, email, service_id) VALUES (?, ?, ?)", consultants)
        conn.commit()

        availability_data = []

        for day in range(0,5): #working from monday to friday
            availability_data.append((1, day, '10:00', '13:00'))
            availability_data.append((1, day, '14:00', '19:00'))
            availability_data.append((2, day, '10:00', '13:00'))
            availability_data.append((2, day, '14:00', '19:00'))
            availability_data.append((3, day, '10:00', '13:00'))
            availability_data.append((3, day, '14:00', '19:00'))
            availability_data.append((4, day, '10:00', '13:00'))
            availability_data.append((4, day, '14:00', '19:00'))
            availability_data.append((5, day, '10:00', '13:00'))
            availability_data.append((5, day, '14:00', '19:00'))
            availability_data.append((6, day, '10:00', '13:00'))
            availability_data.append((6, day, '14:00', '19:00'))
        
        for day in [5,6]: # Emilie and Amanda working on weekends
            availability_data.append((7, day, '10:00', '13:00'))
            availability_data.append((7, day, '14:00', '19:00'))
            availability_data.append((8, day, '10:00', '13:00'))
            availability_data.append((8, day, '14:00', '19:00'))

        cursor.executemany("INSERT INTO consultant_availability (consultant_id, day_of_week, start_time, end_time) VALUES (?,?,?,?)", availability_data)
        conn.commit()

    except sqlite3.IntegrityError:
        print("Data already seeded. Skipping population.")

    finally:
        conn.close()
        print("Database initialization complete. Connection closed.")

    

if __name__ == "__main__":
    initialize_database()
