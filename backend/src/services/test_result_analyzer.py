"""Service to analyze test results and extract relevant information."""

from typing import Dict, Optional, List, Any
import re
import json

from ..models.execution import ExecutionLog
from ..execution import LogType


class TestResultAnalyzer:
    """Analyzes test results and extracts relevant information."""

    @staticmethod
    def analyze_test_failure(logs: List[ExecutionLog]) -> Dict[str, Any]:
        """
        Analyzes test logs to extract:
        - Error type (syntax, logic, import, etc)
        - Affected files
        - Main error messages
        - Correction suggestions
        """
        error_info = {
            "error_type": None,
            "affected_files": [],
            "error_messages": [],
            "test_failures": [],
            "suggestions": []
        }

        for log in logs:
            if log.type == LogType.ERROR:
                # Extract error type
                if "SyntaxError" in log.content:
                    error_info["error_type"] = "syntax"
                elif "ImportError" in log.content or "ModuleNotFoundError" in log.content:
                    error_info["error_type"] = "import"
                elif "AttributeError" in log.content:
                    error_info["error_type"] = "attribute"
                elif "TypeError" in log.content:
                    error_info["error_type"] = "type"
                elif "ValueError" in log.content:
                    error_info["error_type"] = "value"
                elif "KeyError" in log.content:
                    error_info["error_type"] = "key"
                elif "test failed" in log.content.lower() or "assertion" in log.content.lower():
                    error_info["error_type"] = "test_failure"
                elif "failed" in log.content.lower():
                    error_info["error_type"] = "general_failure"

                # Extract files mentioned in error
                # Match common file paths
                file_patterns = [
                    r'File "[^"]+\.(?:py|ts|tsx|js|jsx)"',  # Python/JS file references
                    r'[a-zA-Z0-9_/\\]+\.(?:py|ts|tsx|js|jsx)',  # General file paths
                    r'in (?:module|file) (\S+\.(?:py|ts|tsx|js|jsx))',  # Module references
                ]

                for pattern in file_patterns:
                    matches = re.findall(pattern, log.content)
                    for match in matches:
                        # Clean up the file path
                        if match.startswith('File "'):
                            match = match[6:-1]  # Remove 'File "' and '"'
                        if match not in error_info["affected_files"]:
                            error_info["affected_files"].append(match)

                # Collect error messages (limit length for context)
                error_msg = log.content[:1000] if len(log.content) > 1000 else log.content
                if error_msg not in error_info["error_messages"]:
                    error_info["error_messages"].append(error_msg)

            # Also check INFO logs for test-specific failures
            elif log.type == LogType.INFO:
                if "FAILED" in log.content or "✗" in log.content or "FAIL" in log.content:
                    # Extract test name if possible
                    test_match = re.search(r'(test_\w+|describe.*?(?:it|test)\(.*?\))', log.content)
                    if test_match:
                        error_info["test_failures"].append(test_match.group(1))

        # Generate suggestions based on error type
        if error_info["error_type"]:
            error_info["suggestions"] = TestResultAnalyzer._generate_suggestions(error_info)

        return error_info

    @staticmethod
    def _generate_suggestions(error_info: Dict) -> List[str]:
        """Generate suggestions based on the error type."""
        suggestions = []

        error_type = error_info["error_type"]

        if error_type == "syntax":
            suggestions.append("Check for syntax errors like missing colons, parentheses, or indentation issues")
        elif error_type == "import":
            suggestions.append("Verify that all imported modules are installed and paths are correct")
            suggestions.append("Check if the import statements match the actual module/file structure")
        elif error_type == "attribute":
            suggestions.append("Verify that the object has the attribute being accessed")
            suggestions.append("Check for typos in attribute names")
        elif error_type == "type":
            suggestions.append("Check that function arguments are of the correct type")
            suggestions.append("Verify type annotations and runtime types match")
        elif error_type == "test_failure":
            suggestions.append("Review test assertions and expected values")
            suggestions.append("Check if the implementation matches the test requirements")

        return suggestions

    @staticmethod
    def generate_fix_description(error_info: Dict) -> str:
        """Generate a description for the fix card based on the error."""
        description_parts = [
            "## 🔧 Contexto do Erro",
            "Este card foi criado automaticamente devido a falhas nos testes.",
            ""
        ]

        if error_info.get("error_type"):
            error_type_display = error_info["error_type"].replace("_", " ").title()
            description_parts.append(f"**Tipo de erro:** {error_type_display}")
            description_parts.append("")

        if error_info.get("affected_files"):
            description_parts.append("### 📁 Arquivos Afetados")
            for file in list(set(error_info["affected_files"]))[:10]:  # Limit to 10 files
                description_parts.append(f"- `{file}`")
            description_parts.append("")

        if error_info.get("test_failures"):
            description_parts.append("### ❌ Testes que Falharam")
            for test in list(set(error_info["test_failures"]))[:10]:  # Limit to 10 tests
                description_parts.append(f"- `{test}`")
            description_parts.append("")

        if error_info.get("error_messages"):
            description_parts.append("### 📝 Mensagens de Erro")
            for i, msg in enumerate(error_info["error_messages"][:3], 1):  # Limit to 3 messages
                description_parts.append(f"#### Erro {i}:")
                description_parts.append("```")
                # Clean up the message for better readability
                clean_msg = msg.strip()
                if len(clean_msg) > 500:
                    clean_msg = clean_msg[:497] + "..."
                description_parts.append(clean_msg)
                description_parts.append("```")
                description_parts.append("")

        if error_info.get("suggestions"):
            description_parts.append("### 💡 Sugestões de Correção")
            for suggestion in error_info["suggestions"]:
                description_parts.append(f"- {suggestion}")
            description_parts.append("")

        description_parts.extend([
            "## 📋 Ação Necessária",
            "",
            "1. Analise os erros reportados acima",
            "2. Identifique a causa raiz do problema",
            "3. Implemente as correções necessárias",
            "4. Execute os testes novamente para validar a correção",
            "",
            "---",
            "",
            "**Nota:** Este card foi gerado automaticamente pelo sistema de CI/CD ao detectar falhas nos testes."
        ])

        return "\n".join(description_parts)

    @staticmethod
    def extract_error_context(logs: List[ExecutionLog]) -> str:
        """Extract a JSON-serializable context from the logs for storage."""
        error_info = TestResultAnalyzer.analyze_test_failure(logs)

        # Create a simplified version for storage
        context = {
            "error_type": error_info.get("error_type"),
            "affected_files": error_info.get("affected_files", [])[:20],  # Limit for storage
            "test_failures": error_info.get("test_failures", [])[:20],
            "error_count": len(error_info.get("error_messages", [])),
            "first_errors": error_info.get("error_messages", [])[:5],  # Store first 5 errors
            "suggestions": error_info.get("suggestions", [])
        }

        try:
            return json.dumps(context, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            # Fallback if serialization fails
            return json.dumps({"error": "Failed to serialize error context"})