"""
Integration with Claude Agent SDK for chat functionality.
This module handles the communication with Claude AI using the Agent SDK.
"""
from typing import AsyncGenerator
from pathlib import Path
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)


class ClaudeAgentChat:
    """Handler for Claude Agent SDK integration"""

    def __init__(self):
        """Initialize the Claude Agent Chat handler"""
        # No need for API key - Agent SDK uses Claude Code authentication
        pass

    async def _stream_response_gemini(
        self,
        messages: list[dict],
        model: str,
        system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response from Gemini using the GeminiAgent.

        Args:
            messages: List of conversation messages
            model: Gemini model to use (e.g., "gemini-3-pro", "gemini-3-flash")
            system_prompt: Optional system prompt

        Yields:
            str: Chunks of the response text as they arrive
        """
        print(f"[ClaudeAgentChat] _stream_response_gemini called with model: {model}")
        print(f"[ClaudeAgentChat] Number of messages: {len(messages)}")

        try:
            from .gemini_agent import GeminiAgent

            # Get current working directory from active project
            from .database import async_session_maker
            from .models.project import ActiveProject
            from sqlalchemy import select

            cwd = Path.cwd()
            print(f"[ClaudeAgentChat] Initial cwd: {cwd}")

            async with async_session_maker() as session:
                result = await session.execute(
                    select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
                )
                active_project = result.scalar_one_or_none()
                if active_project:
                    cwd = Path(active_project.path)
                    print(f"[ClaudeAgentChat] Using project cwd: {cwd}")

            # Initialize Gemini agent
            print(f"[ClaudeAgentChat] Initializing GeminiAgent with model: {model}")
            gemini = GeminiAgent(model=model)

            # Stream response
            print(f"[ClaudeAgentChat] Starting stream...")
            chunk_count = 0
            async for chunk in gemini.chat_completion(messages, system_prompt, cwd):
                chunk_count += 1
                print(f"[ClaudeAgentChat] Yielding chunk {chunk_count}: {chunk[:50]}...")
                yield chunk

            print(f"[ClaudeAgentChat] Stream completed. Total chunks: {chunk_count}")

        except Exception as e:
            error_msg = f"Error in Gemini Agent: {str(e)}"
            print(f"[ClaudeAgentChat] {error_msg}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(error_msg)

    async def stream_response(
        self,
        messages: list[dict],
        model: str = "sonnet-4.5",
        system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Claude or Gemini using Agent SDK directly
        without predefined commands like /question

        Args:
            messages: List of conversation messages in format [{"role": "user/assistant", "content": "..."}]
            model: AI model to use (e.g., "opus-4.5", "sonnet-4.5", "haiku-4.5", "gemini-3-pro", "gemini-3-flash")
            system_prompt: Optional system prompt to set context

        Yields:
            str: Chunks of the response text as they arrive
        """
        print(f"[ClaudeAgentChat] stream_response called with model: {model}")

        # Check if it's a Gemini model
        if model.startswith("gemini"):
            print(f"[ClaudeAgentChat] Detected Gemini model, routing to _stream_response_gemini")
            async for chunk in self._stream_response_gemini(messages, model, system_prompt):
                yield chunk
            return

        try:
            # Get current working directory from active project in database
            from .database import async_session_maker
            from .models.project import ActiveProject
            from sqlalchemy import select

            cwd = Path.cwd()
            async with async_session_maker() as session:
                result = await session.execute(
                    select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
                )
                active_project = result.scalar_one_or_none()
                if active_project:
                    cwd = Path(active_project.path)

            # Map model names to valid Anthropic API model names
            model_mapping = {
                # Claude 4.5 models (using aliases that auto-update to latest snapshot)
                "opus-4.5": "claude-opus-4-5",
                "sonnet-4.5": "claude-sonnet-4-5",
                "haiku-4.5": "claude-haiku-4-5",
                # Claude 3.5 models (for backward compatibility)
                "claude-3.5-opus": "claude-3-5-opus-20240229",
                "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
                "claude-3.5-haiku": "claude-3-5-haiku-20241022",
                # Claude 3 models
                "claude-3-sonnet": "claude-3-sonnet-20240229",
                "claude-3-opus": "claude-3-opus-20240229",
            }
            agent_model = model_mapping.get(model, "claude-sonnet-4-5")

            # Build conversation context
            # Instead of using /question command, send direct prompt with full context
            full_prompt = ""

            # Add system prompt if provided
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n"

            # Add conversation history
            if len(messages) > 1:
                full_prompt += "Previous conversation:\n"
                for msg in messages[:-1]:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    full_prompt += f"{role}: {msg['content']}\n"
                full_prompt += "\n"

            # Add current user message
            user_message = messages[-1]["content"]
            full_prompt += f"User: {user_message}\n\nAssistant:"

            # Configure Claude Agent SDK Options - same as /plan but with appropriate tools
            options = ClaudeAgentOptions(
                cwd=cwd,  # Use project root
                setting_sources=["user", "project"],
                allowed_tools=[
                    "Read",      # Read files
                    "Bash",      # Execute commands
                    "Glob",      # Search files
                    "Grep",      # Search content
                    "WebSearch", # Web search capability
                    "WebFetch",  # Fetch web content
                    "Task",      # Launch agents for complex tasks
                    "Skill",     # Use skills
                ],
                permission_mode="bypassPermissions",  # Auto-approve for chat
                model=agent_model,
            )

            # Execute query directly without command prefix
            async for message in query(prompt=full_prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Stream text content
                            yield block.text
                elif isinstance(message, ResultMessage):
                    # Log para debug, mas NÃO faz yield do resultado
                    # pois o conteúdo já foi enviado através dos TextBlocks
                    if hasattr(message, "result") and message.result:
                        print(f"[ClaudeAgentChat] ResultMessage received (not yielding): {len(message.result)} chars")

        except Exception as e:
            error_msg = f"Error in Claude Agent SDK: {str(e)}"
            print(f"[ClaudeAgentChat] {error_msg}")
            raise RuntimeError(error_msg)

    async def get_single_response(
        self,
        messages: list[dict],
        model: str = "sonnet-4.5",
        system_prompt: str | None = None
    ) -> str:
        """
        Get a complete response from Claude (non-streaming).

        Args:
            messages: List of conversation messages
            model: AI model to use
            system_prompt: Optional system prompt

        Returns:
            str: The complete response text
        """
        try:
            full_response = ""
            async for chunk in self.stream_response(messages, model, system_prompt):
                full_response += chunk
            return full_response

        except Exception as e:
            error_msg = f"Error in Claude Agent SDK: {str(e)}"
            print(f"[ClaudeAgentChat] {error_msg}")
            raise RuntimeError(error_msg)


# Default system prompt for the chat assistant (kept for reference, not used with /question)
DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant integrated into a Kanban board application.
You can help users with:
- Understanding and managing their tasks
- Planning and organizing their workflow
- Answering questions about software development
- Providing coding assistance and best practices
- General questions and conversations

Be concise, friendly, and helpful. When discussing code, provide clear examples.
Keep responses focused and actionable."""


# Singleton instance
_claude_agent_instance = None


def get_claude_agent() -> ClaudeAgentChat:
    """Get or create the Claude Agent instance"""
    global _claude_agent_instance
    if _claude_agent_instance is None:
        _claude_agent_instance = ClaudeAgentChat()
    return _claude_agent_instance
