"""
Chat API routes for WebSocket-based real-time chat.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
import json
from ..services.chat_service import get_chat_service
from ..schemas.chat import (
    CreateSessionResponse,
    SessionHistoryResponse,
    MessageSchema,
)


router = APIRouter(prefix="/api/chat", tags=["chat"])

# Allowed AI models
ALLOWED_MODELS = [
    "claude-3.5-opus",
    "claude-3.5-sonnet",
    "claude-3.5-haiku",
    # Keep compatibility with old model names
    "claude-3-sonnet",
    "claude-3-opus",
]


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session():
    """
    Create a new chat session.

    Returns:
        CreateSessionResponse: Session ID and creation timestamp
    """
    chat_service = get_chat_service()
    session_data = chat_service.create_session()

    return CreateSessionResponse(
        sessionId=session_data["sessionId"],
        createdAt=session_data["createdAt"],
    )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_chat_history(session_id: str):
    """
    Get the chat history for a session.

    Args:
        session_id: The session ID to retrieve

    Returns:
        SessionHistoryResponse: Session history with all messages

    Raises:
        HTTPException: 404 if session not found
    """
    chat_service = get_chat_service()
    session = chat_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Convert messages to schema format
    messages = [
        MessageSchema(
            id=f"{session_id}-{idx}",
            role=msg["role"],
            content=msg["content"],
            timestamp=msg["timestamp"],
        )
        for idx, msg in enumerate(session["messages"])
    ]

    return SessionHistoryResponse(
        sessionId=session_id,
        messages=messages,
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """
    Delete a chat session.

    Args:
        session_id: The session ID to delete

    Returns:
        JSON: Success message

    Raises:
        HTTPException: 404 if session not found
    """
    chat_service = get_chat_service()
    success = chat_service.delete_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return JSONResponse(
        content={"message": "Session deleted successfully"},
        status_code=200,
    )


@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat with streaming responses.

    The WebSocket expects JSON messages with format:
    {
        "type": "message",
        "content": "user message text",
        "model": "claude-3-sonnet" (optional, defaults to claude-3-sonnet)
    }

    And sends back JSON responses:
    {
        "type": "chunk" | "end" | "error",
        "content": "response chunk text" (for chunk type),
        "messageId": "unique-message-id",
        "message": "error message" (for error type)
    }

    Args:
        websocket: The WebSocket connection
        session_id: The chat session ID
    """
    chat_service = get_chat_service()
    await websocket.accept()

    print(f"[ChatWebSocket] Client connected to session: {session_id}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                message_type = message_data.get("type")
                message_content = message_data.get("content")
                message_model = message_data.get("model", "claude-3.5-sonnet")

                if message_type != "message" or not message_content:
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "message": "Invalid message format",
                        })
                    )
                    continue

                # Validate model
                if message_model not in ALLOWED_MODELS:
                    await websocket.send_text(
                        json.dumps({
                            "type": "error",
                            "message": f"Invalid model: {message_model}. Allowed models: {', '.join(ALLOWED_MODELS)}",
                        })
                    )
                    continue

                # Stream response from chat service with selected model
                async for chunk in chat_service.send_message(
                    session_id=session_id,
                    message=message_content,
                    model=message_model,
                ):
                    await websocket.send_text(json.dumps(chunk))

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                    })
                )
            except Exception as e:
                error_msg = f"Error processing message: {str(e)}"
                print(f"[ChatWebSocket] {error_msg}")
                await websocket.send_text(
                    json.dumps({
                        "type": "error",
                        "message": error_msg,
                    })
                )

    except WebSocketDisconnect:
        print(f"[ChatWebSocket] Client disconnected from session: {session_id}")
    except Exception as e:
        print(f"[ChatWebSocket] Unexpected error: {str(e)}")
        try:
            await websocket.close()
        except:
            pass


@router.get("/sessions")
async def list_sessions():
    """
    List all active chat sessions (for debugging/admin purposes).

    Returns:
        JSON: List of session IDs and count
    """
    chat_service = get_chat_service()
    sessions = chat_service.list_sessions()

    return JSONResponse(
        content={
            "sessions": sessions,
            "count": len(sessions),
        },
        status_code=200,
    )
