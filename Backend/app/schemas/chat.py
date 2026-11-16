"""
Pydantic schemas for Chat requests and responses.
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request for the chatbot endpoint."""
    message: str = Field(..., min_length=1, max_length=4096)
    session_id: str = Field(..., description="Session identifier for conversation context")


class ChatResponse(BaseModel):
    """Response from the chatbot endpoint."""
    session_id: str
    reply: str
    model: str
    context_used: bool = False
