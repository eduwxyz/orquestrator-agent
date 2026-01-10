"""Serviço de agregação de métricas."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
import statistics

from ..models.metrics import ExecutionMetrics
from ..repositories.metrics_repository import MetricsRepository


class MetricsAggregator:
    """Serviço para agregar e analisar métricas."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = MetricsRepository(db)

    async def aggregate_hourly_metrics(self, project_id: str, target_date: date) -> List[Dict[str, Any]]:
        """Agrega métricas por hora para análise de padrões."""
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=1)

        query = select(
            func.extract('hour', ExecutionMetrics.started_at).label('hour'),
            func.count(ExecutionMetrics.id).label('execution_count'),
            func.sum(ExecutionMetrics.total_tokens).label('total_tokens'),
            func.sum(ExecutionMetrics.estimated_cost_usd).label('total_cost'),
            func.avg(ExecutionMetrics.duration_ms).label('avg_duration')
        ).where(
            and_(
                ExecutionMetrics.project_id == project_id,
                ExecutionMetrics.started_at >= start_datetime,
                ExecutionMetrics.started_at < end_datetime
            )
        ).group_by('hour').order_by('hour')

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "hour": int(row.hour),
                "executionCount": row.execution_count or 0,
                "totalTokens": row.total_tokens or 0,
                "totalCost": float(row.total_cost or 0),
                "avgDuration": int(row.avg_duration or 0)
            }
            for row in rows
        ]

    async def calculate_token_trends(
        self,
        project_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Calcula tendências de uso de tokens."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Buscar dados diários
        query = select(
            func.date(ExecutionMetrics.started_at).label('date'),
            func.sum(ExecutionMetrics.total_tokens).label('total_tokens')
        ).where(
            and_(
                ExecutionMetrics.project_id == project_id,
                ExecutionMetrics.started_at >= start_date
            )
        ).group_by('date').order_by('date')

        result = await self.db.execute(query)
        rows = result.all()

        if not rows:
            return {
                "movingAverage": 0,
                "peakUsage": {"date": None, "tokens": 0},
                "trend": 0,
                "projection": 0
            }

        # Calcular média móvel
        token_values = [row.total_tokens or 0 for row in rows]
        moving_avg = statistics.mean(token_values) if token_values else 0

        # Identificar pico de uso
        peak_row = max(rows, key=lambda r: r.total_tokens or 0)
        peak_usage = {
            "date": peak_row.date if peak_row.date else None,
            "tokens": peak_row.total_tokens or 0
        }

        # Calcular tendência (comparação primeira vs última metade)
        mid_point = len(token_values) // 2
        if mid_point > 0:
            first_half_avg = statistics.mean(token_values[:mid_point])
            second_half_avg = statistics.mean(token_values[mid_point:])
            trend = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        else:
            trend = 0

        # Projeção simples (média dos últimos 3 dias)
        recent_values = token_values[-3:] if len(token_values) >= 3 else token_values
        projection = int(statistics.mean(recent_values)) if recent_values else 0

        return {
            "movingAverage": int(moving_avg),
            "peakUsage": peak_usage,
            "trend": round(trend, 2),
            "projection": projection,
            "dailyData": [
                {
                    "date": row.date if row.date else None,
                    "tokens": row.total_tokens or 0
                }
                for row in rows
            ]
        }

    async def analyze_execution_performance(
        self,
        project_id: str,
        command: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analisa performance de execuções."""
        query = select(ExecutionMetrics.duration_ms).where(
            ExecutionMetrics.project_id == project_id
        )

        if command:
            query = query.where(ExecutionMetrics.command == command)

        result = await self.db.execute(query)
        durations = [row[0] for row in result.all() if row[0] is not None]

        if not durations:
            return {
                "p50": 0,
                "p95": 0,
                "p99": 0,
                "mean": 0,
                "min": 0,
                "max": 0,
                "stdDev": 0,
                "outlierCount": 0,
                "outlierThreshold": 0
            }

        durations_sorted = sorted(durations)
        count = len(durations_sorted)

        # Calcular percentis
        p50_index = int(count * 0.50)
        p95_index = int(count * 0.95)
        p99_index = int(count * 0.99)

        p50 = durations_sorted[p50_index] if p50_index < count else durations_sorted[-1]
        p95 = durations_sorted[p95_index] if p95_index < count else durations_sorted[-1]
        p99 = durations_sorted[p99_index] if p99_index < count else durations_sorted[-1]

        mean = statistics.mean(durations)
        std_dev = statistics.stdev(durations) if len(durations) > 1 else 0

        # Identificar outliers (valores > 2 desvios padrão da média)
        outlier_threshold = mean + (2 * std_dev)
        outliers = [d for d in durations if d > outlier_threshold]

        return {
            "p50": int(p50),
            "p95": int(p95),
            "p99": int(p99),
            "mean": int(mean),
            "min": min(durations),
            "max": max(durations),
            "stdDev": int(std_dev),
            "outlierCount": len(outliers),
            "outlierThreshold": int(outlier_threshold)
        }

    async def calculate_roi_metrics(self, project_id: str) -> Dict[str, Any]:
        """Calcula métricas de ROI."""
        # Buscar métricas agregadas
        aggregated = await self.repo.get_aggregated_metrics(project_id)

        # Buscar custos por modelo
        cost_by_model = await self.repo.get_cost_analysis(project_id, group_by="model")

        # Buscar produtividade
        productivity = await self.repo.get_productivity_metrics(project_id)

        # Calcular custo por card completado
        cards_completed = productivity.get("cardsCompleted", 0)
        total_cost = aggregated.get("totalCost", 0)
        cost_per_card = total_cost / cards_completed if cards_completed > 0 else 0

        # Calcular eficiência por modelo (tokens por dólar)
        model_efficiency = []
        for model_data in cost_by_model:
            cost = model_data.get("totalCost", 0)
            tokens = model_data.get("tokenCount", 0)
            efficiency = tokens / cost if cost > 0 else 0
            model_efficiency.append({
                "model": model_data.get("model"),
                "tokensPerDollar": int(efficiency),
                "costPerToken": cost / tokens if tokens > 0 else 0
            })

        # Estimar economia de tempo (assumindo 2h por card manualmente)
        estimated_manual_hours = cards_completed * 2
        avg_execution_time_hours = aggregated.get("avgExecutionTimeMs", 0) / (1000 * 60 * 60)
        time_saved_hours = estimated_manual_hours - (cards_completed * avg_execution_time_hours)

        return {
            "costPerCard": round(cost_per_card, 2),
            "totalCost": total_cost,
            "cardsCompleted": cards_completed,
            "modelEfficiency": model_efficiency,
            "estimatedTimeSaved": {
                "hours": round(time_saved_hours, 2),
                "manualHours": estimated_manual_hours,
                "aiHours": round(cards_completed * avg_execution_time_hours, 2)
            }
        }

    async def compare_periods(
        self,
        project_id: str,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date
    ) -> Dict[str, Any]:
        """Compara métricas entre dois períodos."""
        # Métricas do período atual
        current_metrics = await self.repo.get_aggregated_metrics(
            project_id, current_start, current_end
        )

        # Métricas do período anterior
        previous_metrics = await self.repo.get_aggregated_metrics(
            project_id, previous_start, previous_end
        )

        # Calcular variações
        def calculate_change(current: float, previous: float) -> Dict[str, Any]:
            if previous == 0:
                return {"value": current, "change": 0, "percentage": 0}

            change = current - previous
            percentage = (change / previous) * 100

            return {
                "value": current,
                "change": change,
                "percentage": round(percentage, 2)
            }

        return {
            "current": current_metrics,
            "previous": previous_metrics,
            "comparison": {
                "totalTokens": calculate_change(
                    current_metrics.get("totalTokens", 0),
                    previous_metrics.get("totalTokens", 0)
                ),
                "totalCost": calculate_change(
                    current_metrics.get("totalCost", 0),
                    previous_metrics.get("totalCost", 0)
                ),
                "avgExecutionTime": calculate_change(
                    current_metrics.get("avgExecutionTimeMs", 0),
                    previous_metrics.get("avgExecutionTimeMs", 0)
                ),
                "successRate": calculate_change(
                    current_metrics.get("successRate", 0),
                    previous_metrics.get("successRate", 0)
                )
            }
        }

    async def generate_insights(self, project_id: str) -> List[Dict[str, str]]:
        """Gera insights automáticos sobre as métricas."""
        insights = []

        # Buscar métricas agregadas
        metrics = await self.repo.get_aggregated_metrics(project_id)

        # Buscar tendências de tokens
        trends = await self.calculate_token_trends(project_id, days=7)

        # Buscar performance
        performance = await self.analyze_execution_performance(project_id)

        # Insight de custo
        total_cost = metrics.get("totalCost", 0)
        if total_cost > 50:
            insights.append({
                "type": "warning",
                "title": "Custo Elevado",
                "message": f"Custo total de ${total_cost:.2f} nas últimas execuções. Considere otimizar prompts ou usar modelos mais econômicos."
            })

        # Insight de tendência
        trend = trends.get("trend", 0)
        if abs(trend) > 20:
            trend_direction = "aumento" if trend > 0 else "redução"
            insights.append({
                "type": "info",
                "title": "Tendência de Uso",
                "message": f"Detectado {trend_direction} de {abs(trend):.1f}% no uso de tokens nos últimos 7 dias."
            })

        # Insight de performance
        p95 = performance.get("p95", 0)
        mean = performance.get("mean", 0)
        if p95 > mean * 2:
            insights.append({
                "type": "optimization",
                "title": "Variação de Performance",
                "message": f"P95 de tempo de execução ({p95}ms) é muito maior que a média ({mean}ms). Verifique execuções lentas."
            })

        # Insight de taxa de sucesso
        success_rate = metrics.get("successRate", 0)
        if success_rate < 80:
            insights.append({
                "type": "warning",
                "title": "Taxa de Sucesso Baixa",
                "message": f"Taxa de sucesso de {success_rate:.1f}% está abaixo do ideal. Investigue erros recentes."
            })

        # Insight de pico de uso
        peak = trends.get("peakUsage", {})
        peak_tokens = peak.get("tokens", 0)
        avg_tokens = trends.get("movingAverage", 0)
        if peak_tokens > avg_tokens * 3:
            insights.append({
                "type": "info",
                "title": "Pico de Uso Detectado",
                "message": f"Pico de {peak_tokens} tokens em {peak.get('date')} - 3x acima da média."
            })

        return insights
