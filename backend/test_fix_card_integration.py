#!/usr/bin/env python3
"""Test script for fix card creation functionality."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.execution import LogType
from src.models.execution import ExecutionLog
from src.services.test_result_analyzer import TestResultAnalyzer


async def test_analyzer():
    """Test the TestResultAnalyzer functionality."""

    print("Testing TestResultAnalyzer...")

    # Create sample logs with test failure
    logs = [
        ExecutionLog(
            timestamp="2024-12-30T12:00:00",
            type=LogType.ERROR,
            content="FAILED tests/test_auth.py::test_login - AssertionError: Login failed"
        ),
        ExecutionLog(
            timestamp="2024-12-30T12:00:01",
            type=LogType.ERROR,
            content="SyntaxError: invalid syntax in file app.py line 45"
        ),
        ExecutionLog(
            timestamp="2024-12-30T12:00:02",
            type=LogType.INFO,
            content="Test run completed with failures"
        )
    ]

    analyzer = TestResultAnalyzer()

    # Test analyze_test_failure
    print("\n1. Testing analyze_test_failure...")
    error_info = analyzer.analyze_test_failure(logs)
    print(f"   Error type detected: {error_info['error_type']}")
    print(f"   Affected files: {error_info['affected_files']}")
    print(f"   Error messages count: {len(error_info['error_messages'])}")

    # Test generate_fix_description
    print("\n2. Testing generate_fix_description...")
    description = analyzer.generate_fix_description(error_info)
    print("   Description generated successfully")
    print("   Description preview (first 200 chars):")
    print(f"   {description[:200]}...")

    # Check if required elements are present
    print("\n3. Validating generated description...")
    checks = [
        ("Contains error context", "Contexto do Erro" in description),
        ("Contains error type", error_info["error_type"] and f"Tipo de erro:" in description),
        ("Contains action section", "Ação Necessária" in description),
    ]

    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"   {status} {check_name}")

    print("\nTestResultAnalyzer test completed!")

    return error_info, description


async def test_fix_card_creation():
    """Test the fix card creation in agent.py."""

    print("\n" + "="*60)
    print("Testing Fix Card Creation Integration...")
    print("="*60)

    try:
        from src.agent import execute_test_implementation
        print("✅ Successfully imported execute_test_implementation")
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return

    # Check if the function has the fix card logic
    import inspect
    source = inspect.getsource(execute_test_implementation)

    checks = [
        ("Has TestResultAnalyzer import", "TestResultAnalyzer" in source),
        ("Has analyze_test_failure call", "analyze_test_failure" in source),
        ("Has fix card creation", "is_fix_card" in source or "parent_card_id" in source),
        ("Has error detection", "if not result.success" in source or "ERROR" in source),
    ]

    print("\nCode inspection results:")
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"   {status} {check_name}")

    print("\nIntegration test completed!")


if __name__ == "__main__":
    print("Starting Fix Card Feature Tests...\n")

    # Run tests
    asyncio.run(test_analyzer())
    asyncio.run(test_fix_card_creation())

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)