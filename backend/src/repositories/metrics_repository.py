"""Repository para operações com métricas."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, case
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid

from ..models.metrics import ProjectMetrics, ExecutionMetrics
from ..models.execution import Execution, ExecutionStatus
from ..models.card import Card


class MetricsRepository:
    """Repository para gerenciar métricas do projeto."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_execution_metric(
        self,
        execution_id: str,
        card_id: str,
        project_id: str,
        command: str,
        model_used: str,
        started_at: datetime,
        completed_at: datetime,
        duration_ms: int,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        estimated_cost_usd: Decimal,
        status: str,
        error_message: Optional[str] = None
    ) -> ExecutionMetrics:
        """Cria uma nova métrica de execução."""
        metric = ExecutionMetrics(
            id=str(uuid.uuid4()),
            execution_id=execution_id,
            card_id=card_id,
            project_id=project_id,
            command=command,
            model_used=model_used,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            status=status,
            error_message=error_message,
            created_at=datetime.utcnow()
        )

        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)
        return metric

    async def get_project_metrics(
        self,
        project_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        granularity: Literal["hour", "day", "week", "month"] = "day"
    ) -> List[ProjectMetrics]:
        """Retorna métricas agregadas do projeto."""
        query = select(ProjectMetrics).where(ProjectMetrics.project_id == project_id)

        if start_date:
            query = query.where(ProjectMetrics.metrics_date >= start_date)
        if end_date:
            query = query.where(ProjectMetrics.metrics_date <= end_date)

        query = query.order_by(ProjectMetrics.metrics_date.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_token_usage(
        self,
        project_id: str,
        period: Literal["24h", "7d", "30d", "all"] = "7d",
        group_by: Literal["hour", "day", "model"] = "day"
    ) -> List[Dict[str, Any]]:
        """Retorna uso de tokens agregado por período."""
        # Calcular data de início baseado no período
        now = datetime.utcnow()
        if period == "24h":
            start_date = now - timedelta(hours=24)
        elif period == "7d":
            start_date = now - timedelta(days=7)
        elif period == "30d":
            start_date = now - timedelta(days=30)
        else:
            start_date = None

        # Construir query baseado em group_by
        if group_by == "model":
            query = select(
                ExecutionMetrics.model_used,
                func.sum(ExecutionMetrics.input_tokens).label('input_tokens'),
                func.sum(ExecutionMetrics.output_tokens).label('output_tokens'),
                func.sum(ExecutionMetrics.total_tokens).label('total_tokens'),
                func.count(ExecutionMetrics.id).label('execution_count')
            ).where(ExecutionMetrics.project_id == project_id)

            if start_date:
                query = query.where(ExecutionMetrics.started_at >= start_date)

            query = query.group_by(ExecutionMetrics.model_used)

        elif group_by == "hour":
            query = select(
                func.strftime('%Y-%m-%d %H:00:00', ExecutionMetrics.started_at).label('timestamp'),
                func.sum(ExecutionMetrics.input_tokens).label('input_tokens'),
                func.sum(ExecutionMetrics.output_tokens).label('output_tokens'),
                func.sum(ExecutionMetrics.total_tokens).label('total_tokens')
            ).where(ExecutionMetrics.project_id == project_id)

            if start_date:
                query = query.where(ExecutionMetrics.started_at >= start_date)

            query = query.group_by('timestamp').order_by('timestamp')

        else:  # day
            query = select(
                func.date(ExecutionMetrics.started_at).label('timestamp'),
                func.sum(ExecutionMetrics.input_tokens).label('input_tokens'),
                func.sum(ExecutionMetrics.output_tokens).label('output_tokens'),
                func.sum(ExecutionMetrics.total_tokens).label('total_tokens')
            ).where(ExecutionMetrics.project_id == project_id)

            if start_date:
                query = query.where(ExecutionMetrics.started_at >= start_date)

            query = query.group_by('timestamp').order_by('timestamp')

        result = await self.db.execute(query)
        rows = result.all()

        # Formatar resultado
        data = []
        for row in rows:
            if group_by == "model":
                data.append({
                    "model": row.model_used,
                    "inputTokens": row.input_tokens or 0,
                    "outputTokens": row.output_tokens or 0,
                    "totalTokens": row.total_tokens or 0,
                    "executionCount": row.execution_count or 0
                })
            else:
                data.append({
                    "timestamp": row.timestamp if row.timestamp else None,
                    "inputTokens": row.input_tokens or 0,
                    "outputTokens": row.output_tokens or 0,
                    "totalTokens": row.total_tokens or 0
                })

        return data

    async def get_execution_times(
        self,
        project_id: str,
        command: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retorna tempos de execução por card/comando."""
        query = select(
            ExecutionMetrics.card_id,
            ExecutionMetrics.command,
            ExecutionMetrics.duration_ms,
            ExecutionMetrics.started_at,
            ExecutionMetrics.status,
            Card.title
        ).join(
            Card, ExecutionMetrics.card_id == Card.id
        ).where(
            ExecutionMetrics.project_id == project_id
        )

        if command:
            query = query.where(ExecutionMetrics.command == command)

        query = query.order_by(ExecutionMetrics.started_at.desc()).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "cardId": row.card_id,
                "cardTitle": row.title or "Untitled",
                "command": row.command,
                "durationMs": row.duration_ms,
                "timestamp": row.started_at if isinstance(row.started_at, str) else (row.started_at.isoformat() if row.started_at else None),
                "status": row.status
            }
            for row in rows
        ]

    async def get_cost_analysis(
        self,
        project_id: str,
        group_by: Literal["model", "command", "day"] = "model"
    ) -> List[Dict[str, Any]]:
        """Retorna análise de custos detalhada."""
        if group_by == "model":
            query = select(
                ExecutionMetrics.model_used,
                func.sum(ExecutionMetrics.estimated_cost_usd).label('total_cost'),
                func.sum(ExecutionMetrics.total_tokens).label('total_tokens'),
                func.count(ExecutionMetrics.id).label('execution_count')
            ).where(
                ExecutionMetrics.project_id == project_id
            ).group_by(ExecutionMetrics.model_used)

        elif group_by == "command":
            query = select(
                ExecutionMetrics.command,
                func.sum(ExecutionMetrics.estimated_cost_usd).label('total_cost'),
                func.sum(ExecutionMetrics.total_tokens).label('total_tokens'),
                func.count(ExecutionMetrics.id).label('execution_count')
            ).where(
                ExecutionMetrics.project_id == project_id
            ).group_by(ExecutionMetrics.command)

        else:  # day
            query = select(
                func.date(ExecutionMetrics.started_at).label('date'),
                func.sum(ExecutionMetrics.estimated_cost_usd).label('total_cost'),
                func.sum(ExecutionMetrics.total_tokens).label('total_tokens'),
                func.count(ExecutionMetrics.id).label('execution_count')
            ).where(
                ExecutionMetrics.project_id == project_id
            ).group_by('date').order_by('date')

        result = await self.db.execute(query)
        rows = result.all()

        # Calcular total para percentuais
        total_cost = sum(float(row.total_cost or 0) for row in rows)

        data = []
        for row in rows:
            cost = float(row.total_cost or 0)
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0

            if group_by == "model":
                data.append({
                    "model": row.model_used,
                    "totalCost": cost,
                    "percentage": round(percentage, 2),
                    "tokenCount": row.total_tokens or 0,
                    "executions": row.execution_count or 0
                })
            elif group_by == "command":
                data.append({
                    "command": row.command,
                    "totalCost": cost,
                    "percentage": round(percentage, 2),
                    "tokenCount": row.total_tokens or 0,
                    "executions": row.execution_count or 0
                })
            else:
                data.append({
                    "date": row.date if row.date else None,
                    "totalCost": cost,
                    "percentage": round(percentage, 2),
                    "tokenCount": row.total_tokens or 0,
                    "executions": row.execution_count or 0
                })

        return data

    async def get_aggregated_metrics(
        self,
        project_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Retorna métricas agregadas do projeto."""
        query = select(
            func.sum(ExecutionMetrics.input_tokens).label('total_input_tokens'),
            func.sum(ExecutionMetrics.output_tokens).label('total_output_tokens'),
            func.sum(ExecutionMetrics.total_tokens).label('total_tokens'),
            func.sum(ExecutionMetrics.estimated_cost_usd).label('total_cost'),
            func.avg(ExecutionMetrics.duration_ms).label('avg_execution_time'),
            func.min(ExecutionMetrics.duration_ms).label('min_execution_time'),
            func.max(ExecutionMetrics.duration_ms).label('max_execution_time'),
            func.count(ExecutionMetrics.id).label('total_executions'),
            func.sum(
                case(
                    (ExecutionMetrics.status == 'success', 1),
                    else_=0
                )
            ).label('successful_executions')
        ).where(ExecutionMetrics.project_id == project_id)

        if start_date:
            query = query.where(func.date(ExecutionMetrics.started_at) >= start_date)
        if end_date:
            query = query.where(func.date(ExecutionMetrics.started_at) <= end_date)

        result = await self.db.execute(query)
        row = result.first()

        if not row:
            return {
                "totalInputTokens": 0,
                "totalOutputTokens": 0,
                "totalTokens": 0,
                "totalCost": 0,
                "avgExecutionTimeMs": 0,
                "minExecutionTimeMs": 0,
                "maxExecutionTimeMs": 0,
                "totalExecutions": 0,
                "successfulExecutions": 0,
                "successRate": 0
            }

        total_executions = row.total_executions or 0
        successful_executions = row.successful_executions or 0
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0

        return {
            "totalInputTokens": row.total_input_tokens or 0,
            "totalOutputTokens": row.total_output_tokens or 0,
            "totalTokens": row.total_tokens or 0,
            "totalCost": float(row.total_cost or 0),
            "avgExecutionTimeMs": int(row.avg_execution_time or 0),
            "minExecutionTimeMs": row.min_execution_time or 0,
            "maxExecutionTimeMs": row.max_execution_time or 0,
            "totalExecutions": total_executions,
            "successfulExecutions": successful_executions,
            "successRate": round(success_rate, 2)
        }

    async def get_productivity_metrics(
        self,
        project_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Retorna métricas de produtividade."""
        # Contar cards por status
        cards_query = select(
            Card.status,
            func.count(Card.id).label('count')
        ).where(Card.project_id == project_id)

        if start_date:
            cards_query = cards_query.where(func.date(Card.created_at) >= start_date)
        if end_date:
            cards_query = cards_query.where(func.date(Card.created_at) <= end_date)

        cards_query = cards_query.group_by(Card.status)

        result = await self.db.execute(cards_query)
        status_counts = {row.status: row.count for row in result.all()}

        # Calcular velocidade (cards completados por dia)
        days_range = (end_date - start_date).days if start_date and end_date else 7
        cards_completed = status_counts.get('done', 0)
        velocity = cards_completed / days_range if days_range > 0 else 0

        return {
            "cardsCompleted": cards_completed,
            "cardsInProgress": status_counts.get('in_progress', 0),
            "cardsTodo": status_counts.get('todo', 0),
            "velocity": round(velocity, 2),
            "totalCards": sum(status_counts.values())
        }
