from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import Optional, List
import uuid
from datetime import datetime
from ..models.execution import Execution, ExecutionLog, ExecutionStatus
from ..cache import execution_cache

class ExecutionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution(
        self,
        card_id: str,
        command: str,
        title: str = ""
    ) -> Execution:
        """Cria nova execução e desativa anteriores do mesmo card"""
        # Desativa execuções anteriores
        await self.db.execute(
            update(Execution)
            .where(Execution.card_id == card_id)
            .where(Execution.is_active == True)
            .values(is_active=False)
        )

        execution = Execution(
            id=str(uuid.uuid4()),
            card_id=card_id,
            command=command,
            title=title,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
            is_active=True,
            workflow_stage=command.replace("/", "")  # plan, implement, test, review
        )

        self.db.add(execution)
        await self.db.commit()
        return execution

    async def add_log(
        self,
        execution_id: str,
        log_type: str,
        content: str
    ) -> ExecutionLog:
        """Adiciona log a uma execução e invalida cache"""
        # Busca último sequence
        result = await self.db.execute(
            select(ExecutionLog.sequence)
            .where(ExecutionLog.execution_id == execution_id)
            .order_by(ExecutionLog.sequence.desc())
            .limit(1)
        )
        last_sequence = result.scalar() or 0

        log = ExecutionLog(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            type=log_type,
            content=content,
            sequence=last_sequence + 1,
            timestamp=datetime.utcnow()
        )

        self.db.add(log)
        await self.db.commit()

        # Invalida cache para forçar reload
        execution_result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = execution_result.scalar_one_or_none()
        if execution:
            execution_cache.invalidate(execution.card_id)

        return log

    async def update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        result: Optional[str] = None
    ):
        """Atualiza status de uma execução"""
        values = {
            "status": status,
            "completed_at": datetime.utcnow() if status != ExecutionStatus.RUNNING else None
        }

        if result:
            values["result"] = result

        await self.db.execute(
            update(Execution)
            .where(Execution.id == execution_id)
            .values(**values)
        )
        await self.db.commit()

    async def get_active_execution(self, card_id: str) -> Optional[Execution]:
        """Busca execução ativa de um card"""
        result = await self.db.execute(
            select(Execution)
            .where(Execution.card_id == card_id)
            .where(Execution.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_execution_with_logs(
        self,
        card_id: str
    ) -> Optional[dict]:
        """Busca execução ativa com todos os logs (com cache)"""
        # Tenta cache primeiro
        cached = execution_cache.get(card_id)
        if cached:
            return cached

        execution = await self.get_active_execution(card_id)
        if not execution:
            return None

        # Busca logs
        logs_result = await self.db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.execution_id == execution.id)
            .order_by(ExecutionLog.sequence)
        )
        logs = logs_result.scalars().all()

        result = {
            "cardId": card_id,
            "executionId": execution.id,
            "status": execution.status.value,
            "command": execution.command,
            "workflowStage": execution.workflow_stage,
            "startedAt": execution.started_at.isoformat() if execution.started_at else None,
            "completedAt": execution.completed_at.isoformat() if execution.completed_at else None,
            "result": execution.result,
            "logs": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "type": log.type,
                    "content": log.content
                }
                for log in logs
            ]
        }

        # Adiciona ao cache se ainda running
        if execution.status == ExecutionStatus.RUNNING:
            execution_cache.set(card_id, result)

        return result