import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

from .execution import (
    ExecutionLog,
    ExecutionRecord,
    ExecutionStatus,
    LogType,
    PlanResult,
)

# Store executions in memory
executions: dict[str, ExecutionRecord] = {}


def get_execution(card_id: str) -> Optional[ExecutionRecord]:
    """Get execution record by card ID."""
    return executions.get(card_id)


def get_all_executions() -> list[ExecutionRecord]:
    """Get all execution records."""
    return list(executions.values())


def add_log(record: ExecutionRecord, log_type: LogType, content: str) -> None:
    """Add a log entry to the execution record."""
    log = ExecutionLog(
        timestamp=datetime.now().isoformat(),
        type=log_type,
        content=content,
    )
    record.logs.append(log)

    # Criar prefixo com card_id (primeiros 8 caracteres para brevidade)
    card_id_short = record.card_id[:8] if len(record.card_id) > 8 else record.card_id

    # Se o record tiver título, incluir também (limitado)
    if hasattr(record, 'title') and record.title:
        title_short = record.title[:25] + "..." if len(record.title) > 25 else record.title
        card_prefix = f"[{card_id_short}|{title_short}]"
    else:
        card_prefix = f"[{card_id_short}]"

    print(f"{card_prefix} [Agent] [{log_type.value.upper()}] {content}")


def extract_spec_path(text: str) -> Optional[str]:
    """Extrai o caminho do arquivo de spec do texto de resultado."""
    # Padrões comuns para detectar criação de arquivo de spec
    patterns = [
        r"specs/[\w\-]+\.md",
        r"created.*?(specs/[\w\-]+\.md)",
        r"saved.*?(specs/[\w\-]+\.md)",
        r"File created.*?(specs/[\w\-]+\.md)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Retorna o grupo 1 se existir, senão o match completo
            return match.group(1) if match.lastindex else match.group(0)
    return None


async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute a plan using Claude Agent SDK."""
    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/plan {title}: {description}"

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Initialize execution record
    record = ExecutionRecord(
        cardId=card_id,
        title=title,
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting plan execution for: {title}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""
    spec_path: Optional[str] = None

    try:
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],  # Load Skills from .claude/skills/
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                # Handle assistant messages with content blocks
                for block in message.content:
                    if isinstance(block, TextBlock):
                        add_log(record, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                        # Tentar extrair spec_path do texto
                        if not spec_path:
                            spec_path = extract_spec_path(block.text)
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")
                        # Se for Write tool, captura o file_path
                        if block.name == "Write" and hasattr(block, "input"):
                            tool_input = block.input
                            if isinstance(tool_input, dict) and "file_path" in tool_input:
                                file_path = tool_input["file_path"]
                                if "specs/" in file_path and file_path.endswith(".md"):
                                    spec_path = file_path
                                    add_log(record, LogType.INFO, f"Spec file detected: {spec_path}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    add_log(record, LogType.RESULT, message.result)
                    # Tentar extrair spec_path do resultado
                    if not spec_path:
                        spec_path = extract_spec_path(message.result)

        # Mark as success
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = result_text
        add_log(record, LogType.INFO, "Plan execution completed successfully")
        if spec_path:
            add_log(record, LogType.INFO, f"Spec path: {spec_path}")

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs,
            spec_path=spec_path,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_implement(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /implement command with the spec file path."""
    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/implement {spec_path}"

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem  # Ex: "feature-x" de "specs/feature-x.md"

    # Initialize execution record
    record = ExecutionRecord(
        cardId=card_id,
        title=f"impl:{spec_name}",  # Prefixo para indicar que é implement
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting implementation for: {spec_path}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        add_log(record, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    add_log(record, LogType.RESULT, message.result)

        # Mark as success
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = result_text
        add_log(record, LogType.INFO, "Implementation completed successfully")

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_test_implementation(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /test-implementation command with the spec file path."""
    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/test-implementation {spec_path}"

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem  # Ex: "feature-x" de "specs/feature-x.md"

    # Initialize execution record
    record = ExecutionRecord(
        cardId=card_id,
        title=f"test:{spec_name}",  # Prefixo para indicar que é test
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting test-implementation for: {spec_path}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        add_log(record, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    add_log(record, LogType.RESULT, message.result)

        # Mark as success
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = result_text
        add_log(record, LogType.INFO, "Test-implementation completed successfully")

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_review(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /review command with the spec file path."""
    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/review {spec_path}"

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem  # Ex: "feature-x" de "specs/feature-x.md"

    # Initialize execution record
    record = ExecutionRecord(
        cardId=card_id,
        title=f"review:{spec_name}",  # Prefixo para indicar que é review
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting review for: {spec_path}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        add_log(record, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    add_log(record, LogType.RESULT, message.result)

        # Mark as success
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = result_text
        add_log(record, LogType.INFO, "Review completed successfully")

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )
