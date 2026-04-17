"""Chat API schemas."""

from typing import List, Optional

from pydantic import BaseModel


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
