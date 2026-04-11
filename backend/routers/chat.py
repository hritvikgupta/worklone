"""
Chat Router - Handles chat interactions with Katy PM Agent
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
from backend.services.katy_service import KatyService
from backend.routers.auth import get_current_user
from backend.models.auth_db import AuthDB

router = APIRouter()
db = AuthDB()

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "anonymous"
    conversation_history: Optional[List[dict]] = []
    model: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None
    session_id: Optional[str] = None


class ChatStreamResponse(BaseModel):
    chunk: str
    done: bool


class ChatSessionCreateRequest(BaseModel):
    title: Optional[str] = "New Chat"
    model: Optional[str] = None


# Service instance
katy_service = KatyService()


def _ensure_session_owner(session_id: str, user_id: str):
    session = db.get_chat_session(session_id=session_id, user_id=user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, user=Depends(get_current_user)):
    """
    Send a message to Katy and get a response
    """
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user_id = user["id"]
        if request.session_id:
            _ensure_session_owner(request.session_id, user_id)
        response = await katy_service.chat(
            message=request.message,
            user_id=user_id,
            conversation_history=request.conversation_history or [],
            model=request.model,
            session_id=request.session_id,
        )
        return ChatResponse(response=response, success=True, session_id=request.session_id)
    except Exception as e:
        return ChatResponse(response="", success=False, error=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest, user=Depends(get_current_user)):
    """
    Stream Katy's response (Server-Sent Events)
    """
    from fastapi.responses import StreamingResponse

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["id"]
    if request.session_id:
        _ensure_session_owner(request.session_id, user_id)

    async def event_generator():
        try:
            async for event in katy_service.chat_stream(
                message=request.message,
                user_id=user_id,
                conversation_history=request.conversation_history or [],
                model=request.model,
                session_id=request.session_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/sessions")
async def list_chat_sessions(user=Depends(get_current_user)):
    """List chat sessions for current user."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sessions = db.list_chat_sessions(user_id=user["id"], limit=100)
    return {"success": True, "sessions": sessions}


@router.post("/sessions")
async def create_chat_session(request: ChatSessionCreateRequest, user=Depends(get_current_user)):
    """Create a new chat session."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session_id = db.create_chat_session(
        user_id=user["id"],
        title=request.title or "New Chat",
        model=request.model,
    )
    session = db.get_chat_session(session_id=session_id, user_id=user["id"])
    return {"success": True, "session": session}


@router.get("/sessions/{session_id}/messages")
async def get_chat_session_messages(session_id: str, user=Depends(get_current_user)):
    """Get messages for a chat session."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    _ensure_session_owner(session_id, user["id"])
    history = db.get_chat_history(session_id=session_id, limit=500)
    return {"success": True, "messages": history}


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, user=Depends(get_current_user)):
    """Delete a chat session."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    deleted = db.delete_chat_session(session_id=session_id, user_id=user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"success": True}
