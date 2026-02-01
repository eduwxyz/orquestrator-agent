from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import Optional, List
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from ..models.execution import Execution, ExecutionLog, ExecutionStatus
from ..cache import execution_cache
from ..services.cost_calculator import CostCalculator

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

        # Mapear comando para workflow stage correto
        stage_map = {
            "/plan": "planning",
            "/implement": "implementing",
            "/test-implementation": "testing",
            "/review": "reviewing",
        }
        workflow_stage = stage_map.get(command, command.replace("/", ""))

        execution = Execution(
            id=str(uuid.uuid4()),
            card_id=card_id,
            command=command,
            title=title,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            is_active=True,
            workflow_stage=workflow_stage
        )

        self.db.add(execution)
        await self.db.flush()

        # Invalida cache para forçar reload da nova execução
        execution_cache.invalidate(card_id)

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
            timestamp=datetime.now(timezone.utc)
        )

        self.db.add(log)
        await self.db.flush()

        # Invalida cache para forçar reload
        execution_result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = execution_result.scalar_one_or_none()
        if execution:
            execution_cache.invalidate(execution.card_id)

        return log

    async def get_by_id(self, execution_id: str) -> Optional[Execution]:
        """Busca execução por ID"""
        result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        result: Optional[str] = None,
        workflow_stage: Optional[str] = None
    ):
        """Atualiza status de uma execução"""
        # Busca card_id para invalidar cache
        exec_result = await self.db.execute(
            select(Execution.card_id).where(Execution.id == execution_id)
        )
        card_id = exec_result.scalar_one_or_none()

        values = {
            "status": status,
            "completed_at": datetime.now(timezone.utc) if status != ExecutionStatus.RUNNING else None
        }

        if result:
            values["result"] = result

        if workflow_stage:
            values["workflow_stage"] = workflow_stage

        # Desativa execução quando completa (SUCCESS ou ERROR)
        if status in [ExecutionStatus.SUCCESS, ExecutionStatus.ERROR]:
            values["is_active"] = False

        await self.db.execute(
            update(Execution)
            .where(Execution.id == execution_id)
            .values(**values)
        )
        await self.db.flush()

        # Invalida cache quando execução completa
        if card_id and status in [ExecutionStatus.SUCCESS, ExecutionStatus.ERROR]:
            execution_cache.invalidate(card_id)

    async def update_execution_status_with_metrics(
        self,
        execution_id: str,
        status: ExecutionStatus,
        project_id: str,
        result: Optional[str] = None,
        workflow_stage: Optional[str] = None
    ):
        """
        Atualiza status de uma execução e coleta métricas automaticamente.

        Args:
            execution_id: ID da execução
            status: Novo status
            project_id: ID do projeto para métricas
            result: Resultado da execução (opcional)
            workflow_stage: Estágio do workflow (opcional)
        """
        # Primeiro atualiza o status
        await self.update_execution_status(
            execution_id=execution_id,
            status=status,
            result=result,
            workflow_stage=workflow_stage
        )

        # Se status final (SUCCESS ou ERROR), coleta métricas
        if status in [ExecutionStatus.SUCCESS, ExecutionStatus.ERROR]:
            try:
                from ..services.metrics_collector import MetricsCollector

                # Busca a execução atualizada
                execution = await self.get_by_id(execution_id)
                if execution:
                    collector = MetricsCollector(self.db)
                    await collector.collect_from_execution(execution, project_id)
            except Exception as e:
                # Log erro mas não falha a operação principal
                print(f"[MetricsCollector] Erro ao coletar métricas: {e}")

    async def get_active_execution(self, card_id: str) -> Optional[Execution]:
        """Busca execução ativa de um card (a mais recente)"""
        result = await self.db.execute(
            select(Execution)
            .where(Execution.card_id == card_id)
            .where(Execution.is_active == True)
            .order_by(Execution.started_at.desc())
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
            "title": execution.title,
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

    async def get_execution_history(self, card_id: str) -> List[dict]:
        """Busca todas as execuções de um card com seus logs"""
        result = await self.db.execute(
            select(Execution)
            .where(Execution.card_id == card_id)
            .order_by(Execution.started_at.desc())
        )
        executions = result.scalars().all()

        history = []
        for execution in executions:
            logs_result = await self.db.execute(
                select(ExecutionLog)
                .where(ExecutionLog.execution_id == execution.id)
                .order_by(ExecutionLog.sequence)
            )
            logs = logs_result.scalars().all()

            history.append({
                "executionId": execution.id,
                "command": execution.command,
                "title": execution.title,
                "status": execution.status.value,
                "workflowStage": execution.workflow_stage,
                "startedAt": execution.started_at.isoformat(),
                "completedAt": execution.completed_at.isoformat() if execution.completed_at else None,
                "logs": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "type": log.type,
                        "content": log.content
                    }
                    for log in logs
                ]
            })

        return history

    async def update_token_usage(
        self,
        execution_id: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        model_used: str = None
    ):
        """Atualiza token usage de uma execucao e calcula o custo"""
        values = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }
        if model_used:
            values["model_used"] = model_used

        # Buscar a execução para calcular o custo
        result = await self.db.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = result.scalar_one_or_none()

        if execution and model_used:
            # Calcular custo baseado no modelo e tokens
            from ..config.pricing import calculate_cost
            cost = calculate_cost(model_used, input_tokens, output_tokens)
            values["execution_cost"] = cost

        await self.db.execute(
            update(Execution)
            .where(Execution.id == execution_id)
            .values(**values)
        )
        await self.db.flush()

    async def get_token_stats_for_card(self, card_id: str) -> dict:
        """Retorna estatisticas agregadas de tokens para um card"""
        result = await self.db.execute(
            select(
                func.sum(Execution.input_tokens).label('total_input'),
                func.sum(Execution.output_tokens).label('total_output'),
                func.sum(Execution.total_tokens).label('total_tokens'),
                func.count(Execution.id).label('execution_count')
            ).where(Execution.card_id == card_id)
        )
        row = result.first()

        return {
            "inputTokens": row.total_input or 0,
            "outputTokens": row.total_output or 0,
            "totalTokens": row.total_tokens or 0,
            "executionCount": row.execution_count or 0
        }

    async def get_cost_stats_for_card(self, card_id: str) -> dict:
        """Retorna estatísticas agregadas de custos para um card"""
        # Buscar todas as execuções do card
        result = await self.db.execute(
            select(Execution)
            .where(Execution.card_id == card_id)
        )
        executions = result.scalars().all()

        # Calcular breakdown de custos usando o serviço
        return CostCalculator.calculate_cost_breakdown(executions)