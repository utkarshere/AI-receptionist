# AI Receptionist Assistant 🤖

A full-stack, intelligent AI receptionist capable of holding natural text conversations to manage consulting appointments. Built with **FastAPI**, **Streamlit**, **OpenAI (GPT-4o)**, and **SQLite**.

## 🚀 Features

* **Natural Language Scheduling:** User can book, reschedule, modify, or cancel appointments using conversational English.
* **Intelligent Conflict Resolution:** The AI automatically checks for availability, detects double-bookings, and suggests the next available time slots if a request fails.
* **Stateful Context Awareness:** Maintains conversation history to handle multi-turn dialogue, remembering user details and previous requests within a session.
* **Automated Email Confirmations:** Sends real-time email confirmations with appointment details immediately after a successful booking or change.
* **Robust Guardrails:** Includes specific rules to prevent booking in the past, hallucinating availability, or answering off-topic questions.

## 📂 Project Structure

```text
Receptionist/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt        # Backend python dependencies
│   ├── routes/
│   │   └── chat.py             # Handles text chat endpoints
│   ├── services/
│   │   ├── llm_service.py      # Core AI Orchestrator (Agentic Loop)
│   │   └── email_service.py    # SMTP Handler for email confirmations
│   ├── tests/
│   │   ├── test_db_routes.py   # Endpoints for manual DB testing
│   │   └── test_email.py       # Script to test email functionality
│   └── utils/
│       ├── db_utils.py         # CRUD operations for SQLite
│       └── init_db.py          # Database schema setup & seeding script
├── frontend/
│   ├── app.py                  # Streamlit Chat Interface
│   └── requirements.txt        # Frontend python dependencies
├── data/
│   └── consulting.db           # SQLite Database (auto-generated)
├── .env                        # API Keys & Secrets (gitignored)
└── README.md                   # Project Documentation
```

---

## 🏗️ Architecture & Workflow

The application follows a decoupled Client-Server architecture:

1. **Frontend (Streamlit):** Captures user text input and maintains the active session state. It sends the full conversation history to the backend for processing.
2. **Backend (FastAPI):** Exposes REST endpoints to handle chat turns. It delegates logic to the `llm_service`.
3. **Orchestrator (LLM Service):** Uses OpenAI's GPT-4o in an agentic loop. It "thinks" about the user's request, decides which **Tools** to call, executes them, and generates a final response.
4. **Tools Layer (SQLite & SMTP):**
   * **Database:** Executes SQL queries to check availability, book slots, or retrieve user appointments.
   * **Email:** Sends confirmation emails via SMTP (Gmail) upon successful write operations.

---

## 🛠️ Tech Stack

* **Frontend:** Streamlit
* **Backend:** FastAPI, Uvicorn
* **AI/LLM:** OpenAI API
* **Database:** SQLite (Native Python library)
* **Email:** SMTP (Native Python `smtplib`)

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone [https://github.com/utkarshere/AI-receptionist.git](https://github.com/utkarshere/AI-receptionist.git)
cd Receptionist
```

### 2. Create a Virtual Environment

It is recommended to create a virtual environment for avoiding dependency conflicts.

```
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt

### 4. Setup Environment Variables

Create a `.env` file in the **root** directory (`Receptionist/.env`) and add your credentials:

```plaintext
EMAIL_ADDRESS="your-sender-email@gmail.com"
EMAIL_PASSWORD="your-16-digit-app-password"
**Note:** For Gmail, use an 'App Password' generated from your Google Account Security settings.
```

### 5. Initialize the Database

Run the initialization script once to create the SQLite database and seed it with initial data (consultants, services, etc.).

```powershell
python -m backend.utils.init_db

```

## 🚀 How to Run

You must run the Backend and Frontend in **two separate terminals**.

### Terminal 1: Backend

Start the FastAPI server.

```bash
# Ensure your venv is active
uvicorn backend.main:app --reload
```

The server will start at `http://127.0.0.1:8000`.

### Terminal 2: Frontend

Start the Streamlit user interface

```bash
# Ensure your venv is active
streamlit run frontend/app.py
```

The app will open in your browser at `http://localhost:8501`
