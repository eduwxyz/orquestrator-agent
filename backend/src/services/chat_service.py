"""
Chat service for managing chat sessions and conversations.
Stores sessions in memory (runtime only, no persistence).
Integrates with Kanban to provide context about tasks and activities.
Detects goals and routes them to the orchestrator.
"""
from typing import Dict, List, AsyncGenerator, Optional
from datetime import datetime, timezone
import uuid
from ..agent_chat import get_claude_agent, DEFAULT_SYSTEM_PROMPT
from ..database import async_session_maker
from ..repositories.card_repository import CardRepository
from ..repositories.activity_repository import ActivityRepository
from .goal_classifier_service import get_goal_classifier_service, MessageIntent


class ChatService:
    """Service for managing chat sessions and interactions"""

    def __init__(self):
        """Initialize the chat service with in-memory storage"""
        # Store sessions in memory: session_id -> list of messages
        self.sessions: Dict[str, List[dict]] = {}
        self.claude_agent = get_claude_agent()
        self.goal_classifier = get_goal_classifier_service()
        self._orchestrator_enabled = True  # Can be toggled

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

    def _format_relative_time(self, dt: datetime) -> str:
        """Format datetime as relative time (e.g., 'ha 2 dias')"""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = now - dt

        if diff.days > 0:
            return f"ha {diff.days} dia{'s' if diff.days > 1 else ''}"

        hours = diff.seconds // 3600
        if hours > 0:
            return f"ha {hours}h"

        minutes = diff.seconds // 60
        if minutes > 0:
            return f"ha {minutes}min"

        return "agora"

    def _truncate(self, text: str, max_length: int = 80) -> str:
        """Truncate text adding ... if needed"""
        if not text:
            return ""
        text = text.replace('\n', ' ').strip()
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    async def _get_kanban_context(self) -> str:
        """Fetch current kanban state and format as context"""
        try:
            async with async_session_maker() as session:
                card_repo = CardRepository(session)
                activity_repo = ActivityRepository(session)

                # Fetch all cards
                cards = await card_repo.get_all()

                # Fetch recent activities
                activities = await activity_repo.get_recent_activities(limit=5)

                # Group cards by column
                columns: Dict[str, List] = {
                    "backlog": [], "plan": [], "implement": [],
                    "test": [], "review": [], "done": [],
                    "completed": [], "archived": [], "cancelado": []
                }

                for card in cards:
                    if card.column_id in columns:
                        columns[card.column_id].append(card)

                # Build context
                lines = ["=== KANBAN STATUS ==="]

                # Active columns (excluding completed, archived, cancelado)
                column_config = [
                    ("backlog", "Backlog", "📋"),
                    ("plan", "Plan", "📝"),
                    ("implement", "Implement", "🔨"),
                    ("test", "Test", "🧪"),
                    ("review", "Review", "👀"),
                    ("done", "Done", "✅"),
                ]

                for col_id, col_name, emoji in column_config:
                    col_cards = columns[col_id]
                    if col_cards:
                        lines.append(f"\n{emoji} {col_name} ({len(col_cards)}):")
                        for card in col_cards[:5]:  # Limit to 5 cards per column
                            time_str = self._format_relative_time(card.created_at)
                            lines.append(f"  - \"{card.title}\" ({time_str})")
                            if card.description:
                                desc = self._truncate(card.description, 60)
                                lines.append(f"    -> {desc}")

                # Summary
                active_cols = ["backlog", "plan", "implement", "test", "review", "done"]
                summary = " | ".join([f"{len(columns[c])} {c}" for c in active_cols])
                lines.append(f"\n📊 Resumo: {summary}")

                # Recent activities
                if activities:
                    lines.append("\n🕐 Ultimas atividades:")
                    for act in activities[:5]:
                        time_str = self._format_relative_time(
                            datetime.fromisoformat(act["timestamp"])
                        )
                        card_title = self._truncate(act["cardTitle"], 30)

                        if act["type"] == "moved":
                            lines.append(f"  - \"{card_title}\" movido para {act['toColumn']} ({time_str})")
                        elif act["type"] == "completed":
                            lines.append(f"  - \"{card_title}\" concluido ({time_str})")
                        elif act["type"] == "created":
                            lines.append(f"  - \"{card_title}\" criado ({time_str})")
                        else:
                            lines.append(f"  - \"{card_title}\" {act['type']} ({time_str})")

                lines.append("===================")

                return "\n".join(lines)

        except Exception as e:
            print(f"[ChatService] Error getting kanban context: {e}")
            return ""

    async def get_system_prompt(self) -> str:
        """Get system prompt with kanban context"""
        kanban_context = await self._get_kanban_context()

        if kanban_context:
            return f"{DEFAULT_SYSTEM_PROMPT}\n\n{kanban_context}"

        return DEFAULT_SYSTEM_PROMPT

    async def _submit_goal_to_orchestrator(
        self,
        goal_description: str,
        session_id: str
    ) -> Optional[dict]:
        """Submit a goal to the orchestrator."""
        try:
            from .orchestrator_service import get_orchestrator_service

            async with async_session_maker() as session:
                orchestrator = get_orchestrator_service(session)
                result = await orchestrator.submit_goal(
                    description=goal_description,
                    source="chat",
                    source_id=session_id,
                )
                await session.commit()
                return result
        except Exception as e:
            print(f"[ChatService] Error submitting goal: {e}")
            return None

    async def send_message(
        self,
        session_id: str,
        message: str,
        model: str = "sonnet-4.5"
    ) -> AsyncGenerator[dict, None]:
        """
        Send a message and stream the response from Claude.
        Detects goals and routes them to the orchestrator.

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

        # Check if message is a goal
        if self._orchestrator_enabled:
            classification = self.goal_classifier.classify(message)

            if classification.intent == MessageIntent.GOAL:
                # Submit goal to orchestrator
                goal_result = await self._submit_goal_to_orchestrator(
                    goal_description=classification.goal_description or message,
                    session_id=session_id
                )

                if goal_result:
                    # Yield goal submission notification
                    yield {
                        "type": "goal_submitted",
                        "goalId": goal_result["id"],
                        "description": goal_result["description"],
                        "messageId": str(uuid.uuid4()),
                    }

                    # Add to history
                    self.sessions[session_id].append({
                        "role": "user",
                        "content": message,
                        "timestamp": datetime.now().isoformat(),
                        "model": model,
                        "isGoal": True,
                        "goalId": goal_result["id"],
                    })

                    # Send acknowledgment as assistant message
                    ack_message = (
                        f"Entendido! Recebi seu objetivo e vou trabalhar nele de forma autonoma.\n\n"
                        f"**Objetivo:** {goal_result['description']}\n\n"
                        f"Voce pode acompanhar o progresso no painel do orquestrador ou aqui no chat. "
                        f"Vou decompor esse objetivo em tarefas menores e executar cada uma delas."
                    )

                    assistant_message_id = str(uuid.uuid4())
                    yield {
                        "type": "chunk",
                        "content": ack_message,
                        "messageId": assistant_message_id,
                    }

                    self.sessions[session_id].append({
                        "role": "assistant",
                        "content": ack_message,
                        "timestamp": datetime.now().isoformat(),
                        "model": model,
                        "messageId": assistant_message_id,
                        "goalAcknowledgment": True,
                    })

                    yield {
                        "type": "end",
                        "messageId": assistant_message_id,
                    }
                    return

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

            # Get system prompt with kanban context
            system_prompt = await self.get_system_prompt()

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
