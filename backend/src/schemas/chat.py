from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime


class MessageSchema(BaseModel):
    """Schema for a chat message"""
    id: str
    role: Literal['user', 'assistant']
    content: str
    timestamp: datetime
    model: Optional[str] = None


class ChatSessionSchema(BaseModel):
    """Schema for a chat session"""
    id: str
    messages: list[MessageSchema]
    createdAt: datetime
    updatedAt: datetime
    model: Optional[str] = None


class CreateSessionRequest(BaseModel):
    """Request to create a new chat session"""
    pass


class CreateSessionResponse(BaseModel):
    """Response when creating a chat session"""
    sessionId: str
    createdAt: datetime


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    content: str
    model: Optional[str] = 'sonnet-4.5'


class StreamChunk(BaseModel):
    """A chunk of streamed response"""
    type: Literal['chunk', 'end', 'error']
    content: Optional[str] = None
    messageId: Optional[str] = None
    message: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    """Response with session history"""
    sessionId: str
    messages: list[MessageSchema]
