import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

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

from .repositories.execution_repository import ExecutionRepository
from .models.execution import ExecutionStatus as DBExecutionStatus

# Store executions in memory (mantido para compatibilidade durante migração)
executions: dict[str, ExecutionRecord] = {}


async def get_execution(card_id: str, db_session: Optional[AsyncSession] = None) -> Optional[dict]:
    """Get execution record by card ID from database or memory."""
    if db_session:
        # Usar repository se db_session estiver disponível
        repo = ExecutionRepository(db_session)
        return await repo.get_execution_with_logs(card_id)
    else:
        # Fallback para memória
        record = executions.get(card_id)
        if record:
            return {
                "cardId": record.cardId,
                "status": record.status.value,
                "logs": [
                    {"timestamp": log.timestamp, "type": log.type.value, "content": log.content}
                    for log in record.logs
                ]
            }
        return None


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
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute a plan using Claude Agent SDK."""
    # Obter diretório do projeto atual se houver
    from .project_manager import project_manager as global_project_manager

    if global_project_manager and global_project_manager.current_project:
        cwd = global_project_manager.get_working_directory()
        print(f"[Agent] Using project directory: {cwd}")

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

    # Usar repository se disponível, senão usar memória
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        # Criar execução no banco
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/plan",
            title=title
        )
        # Log inicial no banco
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Starting plan execution for: {title}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Working directory: {cwd}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Prompt: {prompt}"
        )

    # Initialize execution record (memória - para compatibilidade)
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
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="text",
                                content=block.text
                            )
                        result_text += block.text + "\n"
                        # Tentar extrair spec_path do texto
                        if not spec_path:
                            spec_path = extract_spec_path(block.text)
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="tool",
                                content=f"Using tool: {block.name}"
                            )
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

        # Atualizar status no banco se disponível
        if repo and execution_db:
            await repo.update_execution_status(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                result=result_text
            )
            # Busca execução completa para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    result=result_text,
                    logs=execution_data["logs"],
                    spec_path=spec_path,
                )

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

        # Atualizar status de erro no banco se disponível
        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                result=error_message
            )
            # Busca execução para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

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
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute /implement command with the spec file path."""
    # Obter diretório do projeto atual se houver
    from .project_manager import project_manager as global_project_manager

    if global_project_manager and global_project_manager.current_project:
        cwd = global_project_manager.get_working_directory()
        print(f"[Agent] Using project directory: {cwd}")

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


async def create_fix_card_for_test_failure(
    card_id: str,
    logs: list[ExecutionLog],
    spec_path: str,
    execution_error: Optional[str] = None
) -> Optional[str]:
    """Create a fix card when tests fail."""
    from .database import async_session_maker
    from .repositories.card_repository import CardRepository
    from .services.test_result_analyzer import TestResultAnalyzer

    try:
        # Analyze the test failure
        analyzer = TestResultAnalyzer()
        error_info = analyzer.analyze_test_failure(logs)

        # Add execution error if present
        if execution_error:
            error_info["error_messages"].insert(0, f"Execution error: {execution_error}")
            if not error_info["error_type"]:
                error_info["error_type"] = "execution_error"

        # Generate description for the fix card
        description = analyzer.generate_fix_description(error_info)

        # Extract context for storage
        context = analyzer.extract_error_context(logs)

        async with async_session_maker() as session:
            repo = CardRepository(session)

            # Check if there's already an active fix card
            existing_fix = await repo.get_active_fix_card(card_id)
            if existing_fix:
                print(f"[{card_id[:8]}] Fix card already exists: {existing_fix.id}")
                return existing_fix.id

            # Create the fix card
            fix_card = await repo.create_fix_card(
                card_id,
                {
                    "description": description,
                    "context": context
                }
            )

            if fix_card:
                await session.commit()
                print(f"[{card_id[:8]}] Created fix card: {fix_card.id}")
                return fix_card.id
            else:
                print(f"[{card_id[:8]}] Failed to create fix card")
                return None

    except Exception as e:
        print(f"[{card_id[:8]}] Error creating fix card: {e}")
        return None


async def execute_test_implementation(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /test-implementation command with the spec file path."""
    # Obter diretório do projeto atual se houver
    from .project_manager import project_manager as global_project_manager

    if global_project_manager and global_project_manager.current_project:
        cwd = global_project_manager.get_working_directory()
        print(f"[Agent] Using project directory: {cwd}")

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

        # Check if tests failed based on logs
        test_failed = False
        for log in record.logs:
            if log.type == LogType.ERROR or (
                log.type in [LogType.TEXT, LogType.RESULT] and
                any(indicator in log.content.lower() for indicator in [
                    "test failed", "tests failed", "failed test",
                    "assertion error", "✗", "error:", "failed:"
                ])
            ):
                test_failed = True
                break

        # Mark as success or failure based on test results
        record.completed_at = datetime.now().isoformat()

        if test_failed:
            record.status = ExecutionStatus.ERROR
            add_log(record, LogType.ERROR, "Tests failed - creating fix card")

            # Analyze test failure and create fix card
            fix_card_id = await create_fix_card_for_test_failure(card_id, record.logs, spec_path)

            return PlanResult(
                success=False,
                error="Tests failed. A fix card has been created automatically.",
                logs=record.logs,
                fix_card_created=True if fix_card_id else False,
                fix_card_id=fix_card_id
            )
        else:
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

        # Create fix card for execution errors as well
        fix_card_id = await create_fix_card_for_test_failure(
            card_id,
            record.logs,
            spec_path,
            execution_error=error_message
        )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
            fix_card_created=True if fix_card_id else False,
            fix_card_id=fix_card_id
        )


async def execute_review(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /review command with the spec file path."""
    # Obter diretório do projeto atual se houver
    from .project_manager import project_manager as global_project_manager

    if global_project_manager and global_project_manager.current_project:
        cwd = global_project_manager.get_working_directory()
        print(f"[Agent] Using project directory: {cwd}")

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
