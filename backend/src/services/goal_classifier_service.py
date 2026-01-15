"""Service to classify chat messages as goals vs questions."""

import logging
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MessageIntent(str, Enum):
    """Types of message intent."""
    GOAL = "goal"           # User wants something done
    QUESTION = "question"   # User is asking a question
    UNCLEAR = "unclear"     # Can't determine intent


@dataclass
class ClassificationResult:
    """Result of message classification."""
    intent: MessageIntent
    confidence: float  # 0.0 to 1.0
    goal_description: Optional[str]  # Extracted goal if intent is GOAL
    reasoning: str


class GoalClassifierService:
    """
    Service to classify chat messages and detect goals.

    Uses heuristics and keyword matching to determine if a message
    is a goal (actionable task) or a question (information request).
    """

    # Keywords that indicate a goal/task
    GOAL_KEYWORDS = [
        # Portuguese action verbs
        "criar", "adicionar", "implementar", "desenvolver", "fazer",
        "construir", "configurar", "modificar", "alterar", "atualizar",
        "corrigir", "arrumar", "consertar", "refatorar", "otimizar",
        "remover", "deletar", "excluir", "migrar", "integrar",
        "preciso", "quero", "gostaria", "necessito", "desejo",

        # English action verbs
        "create", "add", "implement", "develop", "make", "build",
        "configure", "modify", "change", "update", "fix", "repair",
        "refactor", "optimize", "remove", "delete", "migrate", "integrate",
        "need", "want", "would like", "have to", "must",
    ]

    # Keywords that indicate a question
    QUESTION_KEYWORDS = [
        # Portuguese
        "como", "porque", "por que", "qual", "quais", "onde",
        "quando", "quem", "o que", "explique", "explica",
        "funciona", "significa", "diferenca", "diferencia",

        # English
        "how", "why", "what", "which", "where", "when", "who",
        "explain", "works", "means", "difference", "between",
        "can you tell", "do you know",
    ]

    # Patterns that strongly indicate goals
    GOAL_PATTERNS = [
        r"(preciso|quero|necessito|desejo)\s+(criar|fazer|implementar|adicionar)",
        r"(need|want)\s+to\s+(create|make|implement|add|build)",
        r"(adiciona|cria|implementa|faz)\s+um[a]?\s+",
        r"(add|create|implement|make)\s+(a|an|the)\s+",
        r"^(crie|adicione|implemente|fa[cç]a)",  # Imperative at start
        r"^(create|add|implement|make|build)\s+",
    ]

    # Patterns that strongly indicate questions
    QUESTION_PATTERNS = [
        r"^(como|porque|por que|qual|quais|onde|quando|quem|o que)\s+",
        r"^(how|why|what|which|where|when|who)\s+",
        r"\?$",  # Ends with question mark
        r"(explique|explica|me (diga|fala|conta))",
        r"(explain|tell me|what is|what are)",
    ]

    def classify(self, message: str) -> ClassificationResult:
        """
        Classify a message as a goal or question.

        Args:
            message: The user's message

        Returns:
            ClassificationResult with intent, confidence, and reasoning
        """
        message_lower = message.lower().strip()

        # Score for goal vs question
        goal_score = 0.0
        question_score = 0.0
        reasons = []

        # Check question patterns (strong indicators)
        for pattern in self.QUESTION_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                question_score += 0.3
                reasons.append(f"Matches question pattern: {pattern}")

        # Check goal patterns (strong indicators)
        for pattern in self.GOAL_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                goal_score += 0.3
                reasons.append(f"Matches goal pattern: {pattern}")

        # Count keywords
        goal_keyword_count = sum(
            1 for kw in self.GOAL_KEYWORDS
            if kw in message_lower
        )
        question_keyword_count = sum(
            1 for kw in self.QUESTION_KEYWORDS
            if kw in message_lower
        )

        goal_score += goal_keyword_count * 0.1
        question_score += question_keyword_count * 0.1

        if goal_keyword_count > 0:
            reasons.append(f"Found {goal_keyword_count} goal keywords")
        if question_keyword_count > 0:
            reasons.append(f"Found {question_keyword_count} question keywords")

        # Message length heuristic (goals tend to be longer)
        word_count = len(message.split())
        if word_count > 15:
            goal_score += 0.1
            reasons.append("Longer message (>15 words)")
        elif word_count < 5:
            question_score += 0.1
            reasons.append("Short message (<5 words)")

        # Normalize scores
        total_score = goal_score + question_score
        if total_score > 0:
            goal_confidence = goal_score / total_score
            question_confidence = question_score / total_score
        else:
            goal_confidence = 0.5
            question_confidence = 0.5

        # Determine intent
        if goal_score > question_score and goal_confidence > 0.6:
            intent = MessageIntent.GOAL
            confidence = goal_confidence
            goal_description = self._extract_goal(message)
        elif question_score > goal_score and question_confidence > 0.6:
            intent = MessageIntent.QUESTION
            confidence = question_confidence
            goal_description = None
        else:
            intent = MessageIntent.UNCLEAR
            confidence = max(goal_confidence, question_confidence)
            goal_description = None

        reasoning = "; ".join(reasons) if reasons else "No strong indicators found"

        logger.info(
            f"[GoalClassifier] Intent: {intent.value}, Confidence: {confidence:.2f}, "
            f"Goal: {goal_score:.2f}, Question: {question_score:.2f}"
        )

        return ClassificationResult(
            intent=intent,
            confidence=confidence,
            goal_description=goal_description,
            reasoning=reasoning,
        )

    def _extract_goal(self, message: str) -> str:
        """
        Extract the goal description from a message.

        Cleans up the message to be a clear goal statement.
        """
        # Remove common prefixes
        prefixes_to_remove = [
            r"^(eu\s+)?(preciso|quero|gostaria|necessito)\s+(de\s+)?",
            r"^(i\s+)?(need|want|would like)\s+(to\s+)?",
            r"^(por favor|please)\s*,?\s*",
            r"^(pode|poderia|voce pode|can you|could you)\s+",
        ]

        goal = message
        for prefix in prefixes_to_remove:
            goal = re.sub(prefix, "", goal, flags=re.IGNORECASE)

        return goal.strip()

    def is_goal(self, message: str) -> bool:
        """Simple check if message is a goal."""
        result = self.classify(message)
        return result.intent == MessageIntent.GOAL


def get_goal_classifier_service() -> GoalClassifierService:
    """Get goal classifier service instance."""
    return GoalClassifierService()
