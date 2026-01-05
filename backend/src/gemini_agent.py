"""
Gemini Agent Integration Module

This module provides integration with Gemini CLI for executing commands
and performing chat completions using Google's Gemini models.
"""

import subprocess
import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any


class GeminiAgent:
    """Handler para integração com Gemini CLI"""

    def __init__(self, model: str = "gemini-1.5-pro"):
        """
        Initialize GeminiAgent with specified model.

        Args:
            model: Gemini model identifier (e.g., "gemini-1.5-pro", "gemini-1.5-flash")
        """
        self.model = model
        self.gemini_cli_path = "gemini"  # Assumindo que está no PATH

    async def execute_command(
        self,
        command: str,
        arguments: str,
        cwd: Optional[Path] = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Executa um comando usando Gemini CLI via subprocess.

        Args:
            command: Nome do comando (ex: "plan", "implement")
            arguments: Argumentos do comando
            cwd: Diretório de trabalho
            stream: Se deve fazer streaming da resposta

        Yields:
            String chunks da resposta do comando

        Raises:
            RuntimeError: Se o Gemini CLI retornar erro
        """
        # Monta o comando completo
        cmd_parts = [
            self.gemini_cli_path,
            "run",
            f"--command={command}",
            f"--model={self.model}",
        ]

        if cwd:
            cmd_parts.extend(["--cwd", str(cwd)])

        # Adiciona argumentos
        cmd_parts.append(arguments)

        # Executa o processo
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd
        )

        if stream:
            # Stream output line by line
            if process.stdout:
                async for line in process.stdout:
                    yield line.decode('utf-8')
        else:
            # Retorna output completo
            stdout, stderr = await process.communicate()
            if stderr:
                raise RuntimeError(f"Gemini CLI error: {stderr.decode('utf-8')}")
            yield stdout.decode('utf-8')

    async def chat_completion(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Realiza chat completion usando Gemini.

        Args:
            messages: Lista de mensagens no formato [{"role": "user", "content": "..."}]
            system_prompt: Prompt de sistema opcional

        Yields:
            String chunks da resposta do chat
        """
        # Formata mensagens para o formato esperado pelo Gemini
        formatted_prompt = self._format_messages(messages, system_prompt)

        # Usa comando question para chat
        async for chunk in self.execute_command(
            command="question",
            arguments=formatted_prompt,
            stream=True
        ):
            yield chunk

    def _format_messages(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Formata mensagens para o formato do Gemini.

        Args:
            messages: Lista de mensagens
            system_prompt: Prompt de sistema opcional

        Returns:
            String formatada com todas as mensagens
        """
        parts = []

        if system_prompt:
            parts.append(f"System: {system_prompt}\n")

        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            parts.append(f"{role}: {msg['content']}\n")

        return "\n".join(parts)
