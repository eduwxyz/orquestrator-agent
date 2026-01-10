import { useState, useEffect } from 'react';
import { metricsApi } from '../api/metrics';

interface DashboardMetricsData {
  tokenData: any;
  costData: any;
  executionData: any;
  insights: any;
  isLoading: boolean;
}

/**
 * Hook to fetch and manage dashboard metrics data
 * Auto-refreshes every 30 seconds
 */
export const useDashboardMetrics = (projectId: string = 'current'): DashboardMetricsData => {
  const [data, setData] = useState<{
    tokenData: any;
    costData: any;
    executionData: any;
    insights: any;
  }>({
    tokenData: null,
    costData: null,
    executionData: null,
    insights: null,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        // Fetch all metrics in parallel using existing API
        const [tokens, costs, executions, executionTimes] = await Promise.all([
          metricsApi.getTokenUsage(projectId, '7d', 'day'),
          metricsApi.getCostAnalysis(projectId, 'model'),
          metricsApi.getExecutionPerformance(projectId),
          metricsApi.getExecutionTimes(projectId, undefined, 10),
        ]);

        // Transform token data to match component expectations
        const transformedTokenData = tokens?.data ? {
          daily_usage: tokens.data.map((item: any) => ({
            day: item.timestamp,
            tokens: item.totalTokens,
            input_tokens: item.inputTokens,
            output_tokens: item.outputTokens,
          })),
          total_tokens: tokens.data.reduce((sum: number, item: any) => sum + (item.totalTokens || 0), 0),
          total_cost: 0, // Will be calculated from cost data
        } : null;

        // Transform cost data to match component expectations
        const transformedCostData = costs?.data ? {
          by_model: costs.data
            .filter((item: any) => item.model !== 'unknown')
            .map((item: any) => ({
              model: item.model,
              total_cost: item.totalCost,
              percentage: item.percentage,
            })),
          total_cost: costs.data.reduce((sum: number, item: any) => sum + (item.totalCost || 0), 0),
        } : null;

        // Update total_cost in token data
        if (transformedTokenData && transformedCostData) {
          transformedTokenData.total_cost = transformedCostData.total_cost;
        }

        // Transform execution data to match component expectations
        const transformedExecutionData = executions ? {
          avg_duration_ms: executions.mean || 0,
          p95_duration_ms: executions.p95 || 0,
          success_rate: 100, // Default to 100% if no data
          recent_executions: executionTimes?.data ? executionTimes.data.map((item: any) => ({
            command: item.command,
            duration_ms: item.durationMs,
            timestamp: item.timestamp,
            status: item.status,
          })) : [],
        } : null;

        setData({
          tokenData: transformedTokenData,
          costData: transformedCostData,
          executionData: transformedExecutionData,
          insights: [],
        });
      } catch (error) {
        console.error('Failed to load dashboard metrics:', error);
        // Set empty data on error to prevent UI from breaking
        setData({
          tokenData: null,
          costData: null,
          executionData: null,
          insights: [],
        });
      } finally {
        setIsLoading(false);
      }
    };

    // Initial load
    loadMetrics();

    // Refresh every 30 seconds
    const interval = setInterval(loadMetrics, 30000);

    return () => clearInterval(interval);
  }, [projectId]);

  return { ...data, isLoading };
};
