"""
Gemini service for managing AI interactions with Google Gemini models.
"""
import os
import subprocess
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
import toml


class GeminiService:
    """Service for managing Gemini AI interactions via CLI"""

    def __init__(self):
        """Initialize the Gemini service"""
        self.gemini_cli_path = "gemini"  # Assumindo que está no PATH

    def _get_plan_context(self, cwd: str) -> str:
        """
        Read plan.toml if exists and format as context.

        Args:
            cwd: Working directory path

        Returns:
            str: Formatted plan context or empty string
        """
        plan_path = Path(cwd) / "plan.toml"
        if not plan_path.exists():
            return ""

        try:
            plan_data = toml.load(plan_path)
            context = "\n# Project Configuration (plan.toml)\n"
            for key, value in plan_data.items():
                context += f"{key}: {value}\n"
            return context
        except Exception as e:
            print(f"[GeminiService] Error reading plan.toml: {e}")
            return ""

    def _get_model(self, model_name: str) -> str:
        """
        Map our model names to Gemini CLI model names.

        Args:
            model_name: Our internal model name

        Returns:
            str: CLI model name
        """
        model_map = {
            "gemini-3-pro": "gemini-3-pro-preview",
            "gemini-3-flash": "gemini-3-flash-preview",
        }
        return model_map.get(model_name, "gemini-3-pro-preview")

    async def execute_command(
        self,
        command: str,
        content: str,
        model_name: str,
        cwd: str,
        images: Optional[list] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a command using Gemini CLI.

        Args:
            command: Command to execute (e.g., /plan, /implement, /test, /review)
            content: Content/prompt for the command
            model_name: Model to use
            cwd: Current working directory
            images: Optional list of images

        Yields:
            dict: Stream chunks with type and content
        """
        # Get plan.toml context
        plan_context = self._get_plan_context(cwd)

        # Build the full prompt with context
        full_prompt = f"""
{plan_context}

You are an AI assistant helping with software development tasks.
Current working directory: {cwd}

Command: {command}
{content}
"""

        # Get the CLI model name
        cli_model = self._get_model(model_name)

        # Monta o comando CLI
        cmd_parts = [
            self.gemini_cli_path,
            "-y",  # Auto-approve
            "-p", full_prompt,
            "--model", cli_model,
        ]

        print(f"[GeminiService] Executing Gemini CLI: {' '.join(cmd_parts[:4])}... (prompt truncated)")
        print(f"[GeminiService] Working directory: {cwd}")
        print(f"[GeminiService] Model: {model_name} (CLI: {cli_model})")

        try:
            # Executa o processo
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd
            )

            # Stream output line by line
            if process.stdout:
                print(f"[GeminiService] Streaming output...")
                async for line in process.stdout:
                    decoded = line.decode('utf-8')
                    if decoded.strip():  # Ignora linhas vazias
                        yield {
                            "type": "text",
                            "content": decoded
                        }

            # Check for errors after streaming
            await process.wait()
            if process.returncode != 0 and process.stderr:
                stderr_output = await process.stderr.read()
                error_msg = stderr_output.decode('utf-8')
                print(f"[GeminiService] ERROR: {error_msg}")
                yield {
                    "type": "error",
                    "content": f"Gemini CLI error: {error_msg}"
                }

        except Exception as e:
            yield {
                "type": "error",
                "content": f"Gemini CLI execution error: {str(e)}"
            }


# Singleton instance
_gemini_service_instance = None


def get_gemini_service() -> GeminiService:
    """Get or create the GeminiService singleton instance"""
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance
