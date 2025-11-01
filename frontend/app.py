import streamlit as st
import requests
import os
import json

FASTAPI_BACKEND_URL = os.getenv("FASTAPI_BACKEND_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT = f"{FASTAPI_BACKEND_URL}/chat_turn"

st.set_page_config(page_title="AI Receptionist", layout="wide")
st.title("AI Receptionist Assistant 🤖")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! How can I assist you today?"})

if "session_id" not in st.session_state:
    st.session_state.session_id = None

st.header("Conversation")
chat_container = st.container(height=400, border=True)
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Enter your message here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {
        "session_id": st.session_state.session_id,
        "messages": st.session_state.messages
    }

    try:
        with st.spinner("Assistant is thinking..."):
            response = requests.post(CHAT_ENDPOINT, json=payload)
            response.raise_for_status()

            response_data = response.json()
            ai_msg = response_data.get("response", "Sorry, I couldn't get a response.")

            if st.session_state.session_id is None:
                st.session_state.session_id = response_data.get("session_id")
                print(f"[Streamlit] Received Session ID: {st.session_state.session_id}")

        st.session_state.messages.append({"role": "assistant", "content": ai_msg})
        st.rerun()

    except requests.exceptions.HTTPError as http_err:
         st.error(f"HTTP error occurred: {http_err} - {response.text}")
         error_msg = f"Sorry, there was an error communicating ({response.status_code}). Please try again."
         st.session_state.messages.append({"role": "assistant", "content": error_msg})
         st.rerun()
    except requests.exceptions.RequestException as req_err:
        st.error(f"Connection error: {req_err}")
        error_msg = "Sorry, I couldn't connect to the AI assistant. Please ensure the backend is running and accessible."
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
        st.rerun()