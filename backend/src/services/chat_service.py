"""
Chat service for managing chat sessions and conversations.
Stores sessions in memory (runtime only, no persistence).
"""
from typing import Dict, List, AsyncGenerator
from datetime import datetime
import uuid
from ..agent_chat import get_claude_agent, DEFAULT_SYSTEM_PROMPT


class ChatService:
    """Service for managing chat sessions and interactions"""

    def __init__(self):
        """Initialize the chat service with in-memory storage"""
        # Store sessions in memory: session_id -> list of messages
        self.sessions: Dict[str, List[dict]] = {}
        self.claude_agent = get_claude_agent()

    def create_session(self) -> dict:
        """
        Create a new chat session.

        Returns:
            dict: Session information with id and createdAt timestamp
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = []

        return {
            "sessionId": session_id,
            "createdAt": datetime.now(),
        }

    def get_session(self, session_id: str) -> dict | None:
        """
        Get a chat session by ID.

        Args:
            session_id: The session ID to retrieve

        Returns:
            dict | None: Session data with messages, or None if not found
        """
        if session_id not in self.sessions:
            return None

        return {
            "sessionId": session_id,
            "messages": self.sessions[session_id],
        }

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a chat session.

        Args:
            session_id: The session ID to delete

        Returns:
            bool: True if deleted, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_system_prompt(self) -> str | None:
        """Get system prompt for chat context"""
        # Use the default system prompt defined in agent_chat
        return DEFAULT_SYSTEM_PROMPT

    async def send_message(
        self,
        session_id: str,
        message: str,
        model: str = "claude-3-sonnet"
    ) -> AsyncGenerator[dict, None]:
        """
        Send a message and stream the response from Claude.

        Args:
            session_id: The session ID
            message: The user's message
            model: AI model to use for response

        Yields:
            dict: Stream chunks with type, content, and messageId
        """
        # Create session if it doesn't exist
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        # Add user message to history
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "model": model,
        }
        self.sessions[session_id].append(user_message)

        # Generate assistant response ID
        assistant_message_id = str(uuid.uuid4())
        assistant_content = ""

        try:
            # Prepare messages for Claude (only role and content)
            claude_messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in self.sessions[session_id]
            ]

            # Get system prompt
            system_prompt = self.get_system_prompt()

            # Stream response from Claude with selected model
            async for chunk in self.claude_agent.stream_response(
                messages=claude_messages,
                model=model,
                system_prompt=system_prompt
            ):
                assistant_content += chunk

                # Yield chunk to client
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "messageId": assistant_message_id,
                }

            # Save complete assistant message to session
            assistant_message = {
                "role": "assistant",
                "content": assistant_content,
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "messageId": assistant_message_id,
            }
            self.sessions[session_id].append(assistant_message)

            # Yield end signal
            yield {
                "type": "end",
                "messageId": assistant_message_id,
            }

        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            print(f"[ChatService] {error_message}")

            # Yield error to client
            yield {
                "type": "error",
                "error": str(e),
                "messageId": assistant_message_id,
            }

    def list_sessions(self) -> List[str]:
        """
        List all active session IDs.

        Returns:
            List[str]: List of session IDs
        """
        return list(self.sessions.keys())

    def get_session_count(self) -> int:
        """
        Get the total number of active sessions.

        Returns:
            int: Number of sessions
        """
        return len(self.sessions)


# Singleton instance
_chat_service_instance = None


def get_chat_service() -> ChatService:
    """Get or create the ChatService singleton instance"""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService()
    return _chat_service_instance
