import { useState, useEffect, useCallback, useRef } from 'react';
import { metricsApi } from '../api/metrics';

interface DashboardMetricsData {
  tokenData: any;
  costData: any;
  executionData: any;
  insights: any[];
  productivityData: any;
  isLoading: boolean;
  error: string | null;
  lastUpdate: number;
  refresh: () => Promise<void>;
}

/**
 * Hook to fetch and manage dashboard metrics data
 * Auto-refreshes every 10 seconds
 */
export const useDashboardMetrics = (projectId: string = 'current'): DashboardMetricsData => {
  const [data, setData] = useState<{
    tokenData: any;
    costData: any;
    executionData: any;
    insights: any[];
    productivityData: any;
  }>({
    tokenData: null,
    costData: null,
    executionData: null,
    insights: [],
    productivityData: null,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<number>(0);

  // Track the current request ID to avoid race conditions
  const requestIdRef = useRef(0);

  const loadMetrics = useCallback(async () => {
    // Increment request ID for this load
    const currentRequestId = ++requestIdRef.current;

    console.log('[Dashboard] Loading metrics...', `requestId=${currentRequestId}`);
    setIsLoading(true);
    setError(null);

    const startTime = Date.now();

    try {
      // Fetch all metrics in parallel using existing API
      const [tokens, costs, executions, executionTimes, projectMetrics, insightsData, productivity] = await Promise.all([
        metricsApi.getTokenUsage(projectId, '7d', 'day'),
        metricsApi.getCostAnalysis(projectId, 'model'),
        metricsApi.getExecutionPerformance(projectId),
        metricsApi.getExecutionTimes(projectId, undefined, 10),
        metricsApi.getProjectMetrics(projectId).catch(() => null),
        metricsApi.getInsights(projectId).catch(() => ({ insights: [] })),
        metricsApi.getProductivityMetrics(projectId).catch(() => null),
      ]);

      // Only update state if this is still the latest request
      if (currentRequestId !== requestIdRef.current) {
        console.log('[Dashboard] Request outdated, skipping', `current=${currentRequestId}, latest=${requestIdRef.current}`);
        return;
      }

      console.log(`[Dashboard] Metrics fetched in ${Date.now() - startTime}ms`);

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
        success_rate: projectMetrics?.successRate ?? 100,
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
        insights: insightsData?.insights || [],
        productivityData: productivity || null,
      });

      setLastUpdate(Date.now());
      setError(null);
      console.log('[Dashboard] Metrics loaded successfully');
    } catch (error: any) {
      // Only update error if this is still the latest request
      if (currentRequestId === requestIdRef.current) {
        console.error('[Dashboard] Failed to load metrics:', error);
        setError('Falha ao carregar métricas');
      }
    } finally {
      // Only update loading if this is still the latest request
      if (currentRequestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [projectId]);

  // Manual refresh function
  const refresh = useCallback(async () => {
    await loadMetrics();
  }, [loadMetrics]);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    // Initial load
    loadMetrics();

    // Refresh every 10 seconds
    const interval = setInterval(() => {
      loadMetrics();
    }, 10000);

    return () => {
      clearInterval(interval);
    };
  }, [loadMetrics]);

  return { ...data, isLoading, error, lastUpdate, refresh };
};
