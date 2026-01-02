"""Tests for TestResultAnalyzer service."""

import pytest
from src.services.test_result_analyzer import TestResultAnalyzer
from src.models.execution import ExecutionLog
from src.execution import LogType


class TestTestResultAnalyzer:
    """Test suite for TestResultAnalyzer."""

    def test_analyze_syntax_error(self):
        """Test analysis of syntax errors."""
        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='SyntaxError: invalid syntax in file "test.py", line 10'
            )
        ]

        analyzer = TestResultAnalyzer()
        result = analyzer.analyze_test_failure(logs)

        assert result["error_type"] == "syntax"
        assert "test.py" in result["affected_files"]
        assert len(result["error_messages"]) == 1
        assert "SyntaxError" in result["error_messages"][0]

    def test_analyze_import_error(self):
        """Test analysis of import errors."""
        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='ImportError: No module named "missing_module" in src/main.py'
            )
        ]

        analyzer = TestResultAnalyzer()
        result = analyzer.analyze_test_failure(logs)

        assert result["error_type"] == "import"
        assert "src/main.py" in result["affected_files"]

    def test_analyze_test_failure(self):
        """Test analysis of test failures."""
        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='Test failed: test_user_creation assertion error'
            ),
            ExecutionLog(
                timestamp="2024-01-01T10:00:01",
                type=LogType.INFO,
                content='FAILED test_auth.py::test_login - AssertionError'
            )
        ]

        analyzer = TestResultAnalyzer()
        result = analyzer.analyze_test_failure(logs)

        assert result["error_type"] == "test_failure"
        assert "test_auth.py" in result["affected_files"]
        assert len(result["error_messages"]) == 1
        assert "test_user_creation" in result["error_messages"][0]

    def test_analyze_multiple_errors(self):
        """Test analysis with multiple error types."""
        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='TypeError: unsupported operand type(s) in utils/calc.py'
            ),
            ExecutionLog(
                timestamp="2024-01-01T10:00:01",
                type=LogType.ERROR,
                content='ValueError: invalid literal for int() in main.py'
            ),
            ExecutionLog(
                timestamp="2024-01-01T10:00:02",
                type=LogType.INFO,
                content='Normal info log'
            )
        ]

        analyzer = TestResultAnalyzer()
        result = analyzer.analyze_test_failure(logs)

        assert result["error_type"] == "type"  # First error type found
        assert "utils/calc.py" in result["affected_files"]
        assert "main.py" in result["affected_files"]
        assert len(result["error_messages"]) == 2

    def test_generate_fix_description(self):
        """Test generation of fix card description."""
        error_info = {
            "error_type": "syntax",
            "affected_files": ["test.py", "main.py"],
            "error_messages": ["SyntaxError: invalid syntax"],
            "test_failures": ["test_login", "test_signup"],
            "suggestions": ["Check for syntax errors"]
        }

        analyzer = TestResultAnalyzer()
        description = analyzer.generate_fix_description(error_info)

        assert "🔧 Contexto do Erro" in description
        assert "Tipo de erro: Syntax" in description
        assert "test.py" in description
        assert "main.py" in description
        assert "test_login" in description
        assert "SyntaxError" in description
        assert "Check for syntax errors" in description

    def test_extract_error_context(self):
        """Test extraction of error context for storage."""
        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='SyntaxError: invalid syntax in test.py'
            ),
            ExecutionLog(
                timestamp="2024-01-01T10:00:01",
                type=LogType.ERROR,
                content='Another error message'
            )
        ]

        analyzer = TestResultAnalyzer()
        context_json = analyzer.extract_error_context(logs)

        assert context_json is not None
        assert "error_type" in context_json
        assert "affected_files" in context_json
        assert "error_count" in context_json

    def test_no_errors_found(self):
        """Test analysis when no errors are found."""
        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.INFO,
                content='All tests passed successfully'
            )
        ]

        analyzer = TestResultAnalyzer()
        result = analyzer.analyze_test_failure(logs)

        assert result["error_type"] is None
        assert len(result["affected_files"]) == 0
        assert len(result["error_messages"]) == 0
        assert len(result["suggestions"]) == 0

    def test_file_extraction_patterns(self):
        """Test various file path extraction patterns."""
        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='File "src/components/Card.tsx", line 42'
            ),
            ExecutionLog(
                timestamp="2024-01-01T10:00:01",
                type=LogType.ERROR,
                content='Error in backend/main.py:100'
            ),
            ExecutionLog(
                timestamp="2024-01-01T10:00:02",
                type=LogType.ERROR,
                content='Failed: tests/test_api.js'
            )
        ]

        analyzer = TestResultAnalyzer()
        result = analyzer.analyze_test_failure(logs)

        assert "src/components/Card.tsx" in result["affected_files"]
        assert "backend/main.py" in result["affected_files"]
        assert "tests/test_api.js" in result["affected_files"]

    def test_suggestions_generation(self):
        """Test generation of suggestions based on error type."""
        # Test syntax error suggestions
        logs_syntax = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='SyntaxError: invalid syntax'
            )
        ]

        analyzer = TestResultAnalyzer()
        result_syntax = analyzer.analyze_test_failure(logs_syntax)
        assert any("syntax" in s.lower() for s in result_syntax["suggestions"])

        # Test import error suggestions
        logs_import = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='ImportError: No module named X'
            )
        ]

        result_import = analyzer.analyze_test_failure(logs_import)
        assert any("import" in s.lower() or "module" in s.lower()
                   for s in result_import["suggestions"])

        # Test type error suggestions
        logs_type = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content='TypeError: unsupported operand'
            )
        ]

        result_type = analyzer.analyze_test_failure(logs_type)
        assert any("type" in s.lower() for s in result_type["suggestions"])

    def test_error_message_truncation(self):
        """Test that long error messages are truncated properly."""
        long_error = "Error: " + "x" * 2000  # Very long error message

        logs = [
            ExecutionLog(
                timestamp="2024-01-01T10:00:00",
                type=LogType.ERROR,
                content=long_error
            )
        ]

        analyzer = TestResultAnalyzer()
        result = analyzer.analyze_test_failure(logs)

        assert len(result["error_messages"]) == 1
        assert len(result["error_messages"][0]) <= 1000  # Should be truncated