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

from .models.execution import Execution as ExecutionDB, ExecutionLog as ExecutionLogDB, ExecutionStatus as ExecutionStatusDB
from .database import async_session_maker
from .execution import (
    ExecutionLog,
    ExecutionRecord,
    ExecutionStatus,
    LogType,
    PlanResult,
)


async def get_execution(card_id: str) -> Optional[ExecutionRecord]:
    """Get execution record by card ID from database."""
    async with async_session_maker() as session:
        execution = await session.query(ExecutionDB).filter_by(
            card_id=card_id,
            is_active=True
        ).first()

        if not execution:
            return None

        # Convert to ExecutionRecord format
        logs = await session.query(ExecutionLogDB).filter_by(
            execution_id=execution.id
        ).order_by(ExecutionLogDB.sequence).all()

        return ExecutionRecord(
            cardId=card_id,
            title=execution.command or "",
            startedAt=execution.started_at.isoformat() if execution.started_at else None,
            completedAt=execution.completed_at.isoformat() if execution.completed_at else None,
            status=ExecutionStatus(execution.status.value),
            result=execution.result,
            logs=[
                ExecutionLog(
                    timestamp=log.timestamp.isoformat(),
                    type=LogType(log.type),
                    content=log.content
                )
                for log in logs
            ]
        )


async def get_all_executions() -> list[ExecutionRecord]:
    """Get all active execution records from database."""
    async with async_session_maker() as session:
        executions = await session.query(ExecutionDB).filter_by(is_active=True).all()

        results = []
        for execution in executions:
            logs = await session.query(ExecutionLogDB).filter_by(
                execution_id=execution.id
            ).order_by(ExecutionLogDB.sequence).all()

            results.append(ExecutionRecord(
                cardId=execution.card_id,
                title=execution.command or "",
                startedAt=execution.started_at.isoformat() if execution.started_at else None,
                completedAt=execution.completed_at.isoformat() if execution.completed_at else None,
                status=ExecutionStatus(execution.status.value),
                result=execution.result,
                logs=[
                    ExecutionLog(
                        timestamp=log.timestamp.isoformat(),
                        type=LogType(log.type),
                        content=log.content
                    )
                    for log in logs
                ]
            ))

        return results


async def add_log(execution_id: str, card_id: str, title: str, log_type: LogType, content: str) -> None:
    """Add a log entry to the execution in database."""
    async with async_session_maker() as session:
        # Count existing logs for sequence
        log_count = await session.query(ExecutionLogDB).filter_by(
            execution_id=execution_id
        ).count()

        # Create new log
        log = ExecutionLogDB(
            execution_id=execution_id,
            timestamp=datetime.utcnow(),
            type=log_type.value,
            content=content,
            sequence=log_count
        )
        session.add(log)
        await session.commit()

    # Print log to console
    card_id_short = card_id[:8] if len(card_id) > 8 else card_id
    if title:
        title_short = title[:25] + "..." if len(title) > 25 else title
        card_prefix = f"[{card_id_short}|{title_short}]"
    else:
        card_prefix = f"[{card_id_short}]"

    print(f"{card_prefix} [Agent] [{log_type.value.upper()}] {content}")


def extract_spec_path(text: str) -> Optional[str]:
    """Extrai o caminho do arquivo de spec do texto de resultado."""
    patterns = [
        r"specs/[\w\-]+\.md",
        r"created.*?(specs/[\w\-]+\.md)",
        r"saved.*?(specs/[\w\-]+\.md)",
        r"File created.*?(specs/[\w\-]+\.md)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
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
    """Execute a plan using Claude Agent SDK with database persistence."""
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/plan {title}: {description}"

    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Create execution in database
    async with async_session_maker() as session:
        # Deactivate previous executions for this card
        await session.query(ExecutionDB).filter_by(
            card_id=card_id,
            is_active=True
        ).update({"is_active": False})

        # Create new execution
        execution = ExecutionDB(
            card_id=card_id,
            command="/plan",
            status=ExecutionStatusDB.RUNNING,
            started_at=datetime.utcnow()
        )
        session.add(execution)
        await session.commit()
        execution_id = execution.id

    await add_log(execution_id, card_id, title, LogType.INFO, f"Starting plan execution for: {title}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Working directory: {cwd}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""
    spec_path: Optional[str] = None

    try:
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        await add_log(execution_id, card_id, title, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                        if not spec_path:
                            spec_path = extract_spec_path(block.text)
                    elif isinstance(block, ToolUseBlock):
                        await add_log(execution_id, card_id, title, LogType.TOOL, f"Using tool: {block.name}")
                        if block.name == "Write" and hasattr(block, "input"):
                            tool_input = block.input
                            if isinstance(tool_input, dict) and "file_path" in tool_input:
                                file_path = tool_input["file_path"]
                                if "specs/" in file_path and file_path.endswith(".md"):
                                    spec_path = file_path
                                    await add_log(execution_id, card_id, title, LogType.INFO, f"Spec file detected: {spec_path}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    await add_log(execution_id, card_id, title, LogType.RESULT, message.result)
                    if not spec_path:
                        spec_path = extract_spec_path(message.result)

        # Mark as success
        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.SUCCESS
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = result_text
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.INFO, "Plan execution completed successfully")
        if spec_path:
            await add_log(execution_id, card_id, title, LogType.INFO, f"Spec path: {spec_path}")

        # Get all logs to return
        record = await get_execution(card_id)

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs if record else [],
            spec_path=spec_path,
        )

    except Exception as e:
        error_message = str(e)

        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.ERROR
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = error_message
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.ERROR, f"Execution error: {error_message}")

        record = await get_execution(card_id)

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs if record else [],
        )


async def execute_implement(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /implement command with database persistence."""
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/implement {spec_path}"

    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    spec_name = Path(spec_path).stem
    title = f"impl:{spec_name}"

    # Create execution in database
    async with async_session_maker() as session:
        # Deactivate previous executions for this card
        await session.query(ExecutionDB).filter_by(
            card_id=card_id,
            is_active=True
        ).update({"is_active": False})

        # Create new execution
        execution = ExecutionDB(
            card_id=card_id,
            command="/implement",
            status=ExecutionStatusDB.RUNNING,
            started_at=datetime.utcnow()
        )
        session.add(execution)
        await session.commit()
        execution_id = execution.id

    await add_log(execution_id, card_id, title, LogType.INFO, f"Starting implementation for: {spec_path}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Working directory: {cwd}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        await add_log(execution_id, card_id, title, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        await add_log(execution_id, card_id, title, LogType.TOOL, f"Using tool: {block.name}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    await add_log(execution_id, card_id, title, LogType.RESULT, message.result)

        # Mark as success
        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.SUCCESS
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = result_text
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.INFO, "Implementation completed successfully")

        record = await get_execution(card_id)

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs if record else [],
        )

    except Exception as e:
        error_message = str(e)

        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.ERROR
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = error_message
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.ERROR, f"Execution error: {error_message}")

        record = await get_execution(card_id)

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs if record else [],
        )


async def execute_test_implementation(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /test-implementation command with database persistence."""
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/test-implementation {spec_path}"

    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    spec_name = Path(spec_path).stem
    title = f"test:{spec_name}"

    # Create execution in database
    async with async_session_maker() as session:
        # Deactivate previous executions for this card
        await session.query(ExecutionDB).filter_by(
            card_id=card_id,
            is_active=True
        ).update({"is_active": False})

        # Create new execution
        execution = ExecutionDB(
            card_id=card_id,
            command="/test",
            status=ExecutionStatusDB.RUNNING,
            started_at=datetime.utcnow()
        )
        session.add(execution)
        await session.commit()
        execution_id = execution.id

    await add_log(execution_id, card_id, title, LogType.INFO, f"Starting test-implementation for: {spec_path}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Working directory: {cwd}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        await add_log(execution_id, card_id, title, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        await add_log(execution_id, card_id, title, LogType.TOOL, f"Using tool: {block.name}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    await add_log(execution_id, card_id, title, LogType.RESULT, message.result)

        # Mark as success
        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.SUCCESS
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = result_text
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.INFO, "Test-implementation completed successfully")

        record = await get_execution(card_id)

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs if record else [],
        )

    except Exception as e:
        error_message = str(e)

        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.ERROR
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = error_message
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.ERROR, f"Execution error: {error_message}")

        record = await get_execution(card_id)

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs if record else [],
        )


async def execute_review(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    """Execute /review command with database persistence."""
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/review {spec_path}"

    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    spec_name = Path(spec_path).stem
    title = f"review:{spec_name}"

    # Create execution in database
    async with async_session_maker() as session:
        # Deactivate previous executions for this card
        await session.query(ExecutionDB).filter_by(
            card_id=card_id,
            is_active=True
        ).update({"is_active": False})

        # Create new execution
        execution = ExecutionDB(
            card_id=card_id,
            command="/review",
            status=ExecutionStatusDB.RUNNING,
            started_at=datetime.utcnow()
        )
        session.add(execution)
        await session.commit()
        execution_id = execution.id

    await add_log(execution_id, card_id, title, LogType.INFO, f"Starting review for: {spec_path}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Working directory: {cwd}")
    await add_log(execution_id, card_id, title, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        await add_log(execution_id, card_id, title, LogType.TEXT, block.text)
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        await add_log(execution_id, card_id, title, LogType.TOOL, f"Using tool: {block.name}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    await add_log(execution_id, card_id, title, LogType.RESULT, message.result)

        # Mark as success
        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.SUCCESS
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = result_text
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.INFO, "Review completed successfully")

        record = await get_execution(card_id)

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs if record else [],
        )

    except Exception as e:
        error_message = str(e)

        async with async_session_maker() as session:
            execution = await session.query(ExecutionDB).filter_by(id=execution_id).first()
            execution.status = ExecutionStatusDB.ERROR
            execution.completed_at = datetime.utcnow()
            execution.duration = int((execution.completed_at - execution.started_at).total_seconds())
            execution.result = error_message
            await session.commit()

        await add_log(execution_id, card_id, title, LogType.ERROR, f"Execution error: {error_message}")

        record = await get_execution(card_id)

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs if record else [],
        )