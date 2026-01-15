"""Service to decompose goals into multiple cards using Claude Opus 4.5."""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class DecomposedCard:
    """A card decomposed from a goal."""
    title: str
    description: str
    order: int
    dependencies: List[int]  # Indices of cards this depends on


@dataclass
class DecompositionResult:
    """Result of goal decomposition."""
    success: bool
    cards: List[DecomposedCard]
    reasoning: str
    error: Optional[str] = None


DECOMPOSITION_PROMPT = """Você é um especialista em decomposição de tarefas de desenvolvimento de software.

## Objetivo do Usuário
{goal_description}

## Sua Tarefa
Decomponha este objetivo em cards/tarefas menores e executáveis. Cada card deve ser:
- Específico e bem definido
- Executável de forma independente (quando possível)
- Pequeno o suficiente para ser completado em uma sessão de trabalho

## Regras
1. Crie entre 2 e 7 cards (nem muito poucos, nem muitos)
2. Ordene por dependência (tarefas base primeiro)
3. Cada card deve ter um título claro e descrição detalhada
4. Inclua tarefas de teste quando aplicável

## Formato de Resposta
Responda APENAS com um JSON válido no seguinte formato:
```json
{{
  "reasoning": "Explicação breve de como você decompos o objetivo",
  "cards": [
    {{
      "title": "Título curto e descritivo",
      "description": "Descrição detalhada do que deve ser feito, incluindo critérios de aceitação",
      "order": 1,
      "dependencies": []
    }},
    {{
      "title": "Segundo card",
      "description": "Descrição...",
      "order": 2,
      "dependencies": [1]
    }}
  ]
}}
```

## Contexto do Projeto
Este é um projeto de software. Considere:
- Separar backend e frontend quando aplicável
- Incluir cards para testes
- Considerar migrações de banco de dados se necessário

Responda SOMENTE com o JSON, sem texto adicional antes ou depois."""


class GoalDecomposerService:
    """Service to decompose goals into cards using Claude Opus 4.5."""

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()

    async def decompose(self, goal_description: str) -> DecompositionResult:
        """
        Decompose a goal into multiple cards using Claude Opus 4.5.

        Args:
            goal_description: The goal to decompose

        Returns:
            DecompositionResult with list of cards
        """
        logger.info(f"[GoalDecomposer] Decomposing: {goal_description[:50]}...")

        try:
            # Build prompt
            prompt = DECOMPOSITION_PROMPT.format(goal_description=goal_description)

            # Configure Claude Agent SDK for Opus 4.5
            options = ClaudeAgentOptions(
                cwd=self.cwd,
                setting_sources=["user", "project"],
                allowed_tools=[
                    "Read",   # Allow reading files to understand project
                    "Glob",   # Allow searching files
                    "Grep",   # Allow searching content
                ],
                permission_mode="bypassPermissions",
                model="claude-opus-4-5",
            )

            # Collect response
            full_response = ""
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text

            logger.info(f"[GoalDecomposer] Got response: {len(full_response)} chars")

            # Parse JSON from response
            return self._parse_response(full_response)

        except Exception as e:
            logger.exception(f"[GoalDecomposer] Error: {e}")
            return DecompositionResult(
                success=False,
                cards=[],
                reasoning="",
                error=str(e)
            )

    def _parse_response(self, response: str) -> DecompositionResult:
        """Parse the JSON response from Claude."""
        try:
            # Try to extract JSON from response
            # Sometimes Claude wraps it in markdown code blocks
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find raw JSON
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response

            # Parse JSON
            data = json.loads(json_str)

            # Extract cards
            cards = []
            for card_data in data.get("cards", []):
                card = DecomposedCard(
                    title=card_data.get("title", "Untitled"),
                    description=card_data.get("description", ""),
                    order=card_data.get("order", len(cards) + 1),
                    dependencies=card_data.get("dependencies", []),
                )
                cards.append(card)

            # Sort by order
            cards.sort(key=lambda c: c.order)

            logger.info(f"[GoalDecomposer] Parsed {len(cards)} cards")

            return DecompositionResult(
                success=True,
                cards=cards,
                reasoning=data.get("reasoning", ""),
            )

        except json.JSONDecodeError as e:
            logger.error(f"[GoalDecomposer] JSON parse error: {e}")
            logger.error(f"[GoalDecomposer] Response was: {response[:500]}")

            # Fallback: create single card
            return DecompositionResult(
                success=True,
                cards=[
                    DecomposedCard(
                        title=response[:100] if response else "Task",
                        description=response,
                        order=1,
                        dependencies=[],
                    )
                ],
                reasoning="Failed to parse JSON, created single card",
                error=f"JSON parse error: {e}"
            )


async def decompose_goal(
    goal_description: str,
    cwd: Optional[Path] = None
) -> DecompositionResult:
    """
    Convenience function to decompose a goal.

    Args:
        goal_description: The goal to decompose
        cwd: Working directory for the project

    Returns:
        DecompositionResult with list of cards
    """
    service = GoalDecomposerService(cwd=cwd)
    return await service.decompose(goal_description)
