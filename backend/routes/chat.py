import uuid
from pydantic import BaseModel
from fastapi import APIRouter
from ..utils import db_utils
from ..services import llm_service
from typing import List, Dict

router = APIRouter(
    tags=["Chat"]
)

class ChatTurnInput(BaseModel):
    session_id: str | None = None
    messages: List[Dict[str, str]]

@router.post("/chat_turn")
async def chat_turn_endpoint(payload: ChatTurnInput):
    session_id = payload.session_id
    messages_history = payload.messages

    user_message = ""
    if messages_history and messages_history[-1].get("role") == "user":
        user_message = messages_history[-1].get("content", "")

    if not user_message:
         print("Warning: Received request with empty or invalid message history.")
         return {"session_id": session_id, "response": "I didn't receive a valid message."}

    if not session_id:
        session_id = f"http_session_{uuid.uuid4()}"
        print(f"New chat session started: {session_id}")

    db_utils.add_conversation_message(session_id, "user", user_message)
    print(f"Received from (Session {session_id}): {user_message}")

    ai_response = await llm_service.get_llm_response_with_history(
        session_id=session_id,
        messages_history=messages_history
    )

    if ai_response and ai_response == llm_service.END_CHAT_SIGNAL:
        ai_response = "Thank you for using the service. Goodbye!"
        print(f"Session {session_id} ended by user.")
        db_utils.add_conversation_message(session_id, "ai", ai_response)

    elif ai_response is None:
        ai_response = "Sorry, I encountered an error during processing."
        print(f"Error occurred in LLM service for Session {session_id}.")
        db_utils.add_conversation_message(session_id, "ai", ai_response)

    else:
        print(f"Sending (Session {session_id}): AI: {ai_response}")
        db_utils.add_conversation_message(session_id, "ai", ai_response)

    return {"session_id": session_id, "response": ai_response}