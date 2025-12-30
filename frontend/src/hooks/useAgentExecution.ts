import { useState, useCallback, useRef, useEffect } from "react";
import { Card, ExecutionStatus, ExecutionLog } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3001";
const POLLING_INTERVAL = 1500; // Poll every 1.5 seconds

interface ExecutePlanResult {
  success: boolean;
  specPath?: string;
  result?: string;
  error?: string;
}

interface ExecuteImplementResult {
  success: boolean;
  result?: string;
  error?: string;
}

export function useAgentExecution(initialExecutions?: Map<string, ExecutionStatus>) {
  const [executions, setExecutions] = useState<Map<string, ExecutionStatus>>(
    initialExecutions || new Map()
  );
  const pollingIntervalsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Cleanup polling intervals on unmount
  useEffect(() => {
    return () => {
      pollingIntervalsRef.current.forEach((interval) => clearInterval(interval));
      pollingIntervalsRef.current.clear();
    };
  }, []);

  // Restore polling for running executions
  useEffect(() => {
    if (initialExecutions) {
      initialExecutions.forEach((execution, cardId) => {
        if (execution.status === 'running') {
          console.log(`[useAgentExecution] Restoring polling for card: ${cardId}`);
          startPolling(cardId);
        }
      });
    }
  }, []); // Only run once on mount

  // Function to fetch logs from API
  const fetchLogs = useCallback(async (cardId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/logs/${cardId}`);
      if (!response.ok) return null;
      const data = await response.json();
      if (data.success && data.execution) {
        return data.execution;
      }
      return null;
    } catch (error) {
      console.error(`[useAgentExecution] Failed to fetch logs for ${cardId}:`, error);
      return null;
    }
  }, []);

  // Start polling for a card
  const startPolling = useCallback((cardId: string) => {
    // Don't start if already polling
    if (pollingIntervalsRef.current.has(cardId)) return;

    console.log(`[useAgentExecution] Starting log polling for card: ${cardId}`);

    const interval = setInterval(async () => {
      const execution = await fetchLogs(cardId);
      if (execution) {
        setExecutions((prev) => {
          const next = new Map(prev);
          const current = next.get(cardId);

          // Only update if we have new logs
          if (!current || execution.logs.length > (current.logs?.length || 0)) {
            next.set(cardId, {
              cardId: execution.cardId,
              status: execution.status,
              result: execution.result,
              logs: execution.logs || [],
              startedAt: execution.startedAt,
              completedAt: execution.completedAt,
            });
          }

          // Stop polling if execution completed
          if (execution.status !== 'running') {
            stopPolling(cardId);
          }

          return next;
        });
      }
    }, POLLING_INTERVAL);

    pollingIntervalsRef.current.set(cardId, interval);
  }, [fetchLogs]);

  // Stop polling for a card
  const stopPolling = useCallback((cardId: string) => {
    const interval = pollingIntervalsRef.current.get(cardId);
    if (interval) {
      console.log(`[useAgentExecution] Stopping log polling for card: ${cardId}`);
      clearInterval(interval);
      pollingIntervalsRef.current.delete(cardId);
    }
  }, []);

  const executePlan = useCallback(async (card: Card): Promise<ExecutePlanResult> => {
    console.log(`[useAgentExecution] Starting plan execution for: ${card.title}`);

    // Set status to running with initial log
    const initialLogs: ExecutionLog[] = [
      {
        timestamp: new Date().toISOString(),
        type: "info",
        content: `Iniciando execução do plano para: ${card.title}`,
      },
    ];

    setExecutions((prev) => {
      const next = new Map(prev);
      next.set(card.id, {
        cardId: card.id,
        status: "running",
        logs: initialLogs,
        startedAt: new Date().toISOString(),
      });
      return next;
    });

    // Start polling for real-time logs
    startPolling(card.id);

    try {
      const response = await fetch(`${API_URL}/api/execute-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cardId: card.id,
          title: card.title,
          description: card.description,
        }),
      });

      const result = await response.json();
      const logs: ExecutionLog[] = result.logs || [];

      // Stop polling and update final state
      stopPolling(card.id);

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
          completedAt: new Date().toISOString(),
        });
        return next;
      });

      console.log(`[useAgentExecution] Plan execution completed:`, result);
      return {
        success: result.success,
        specPath: result.specPath,
        result: result.result,
        error: result.error,
      };
    } catch (error) {
      stopPolling(card.id);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      const errorLogs: ExecutionLog[] = [
        ...initialLogs,
        {
          timestamp: new Date().toISOString(),
          type: "error",
          content: `Erro de conexão: ${errorMessage}`,
        },
      ];

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: "error",
          result: errorMessage,
          logs: errorLogs,
        });
        return next;
      });

      console.error(`[useAgentExecution] Error:`, errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [startPolling, stopPolling]);

  const executeImplement = useCallback(async (card: Card): Promise<ExecuteImplementResult> => {
    if (!card.specPath) {
      console.error("[useAgentExecution] Card does not have a specPath");
      return { success: false, error: "Card não possui um plano associado" };
    }

    console.log(`[useAgentExecution] Starting implementation for: ${card.specPath}`);

    // Set status to running with initial log
    const initialLogs: ExecutionLog[] = [
      {
        timestamp: new Date().toISOString(),
        type: "info",
        content: `Iniciando implementação do plano: ${card.specPath}`,
      },
    ];

    setExecutions((prev) => {
      const next = new Map(prev);
      next.set(card.id, {
        cardId: card.id,
        status: "running",
        logs: initialLogs,
        startedAt: new Date().toISOString(),
      });
      return next;
    });

    // Start polling for real-time logs
    startPolling(card.id);

    try {
      const response = await fetch(`${API_URL}/api/execute-implement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cardId: card.id,
          specPath: card.specPath,
        }),
      });

      const result = await response.json();
      const logs: ExecutionLog[] = result.logs || [];

      // Stop polling and update final state
      stopPolling(card.id);

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
          completedAt: new Date().toISOString(),
        });
        return next;
      });

      console.log(`[useAgentExecution] Implementation completed:`, result);
      return {
        success: result.success,
        result: result.result,
        error: result.error,
      };
    } catch (error) {
      stopPolling(card.id);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      const errorLogs: ExecutionLog[] = [
        ...initialLogs,
        {
          timestamp: new Date().toISOString(),
          type: "error",
          content: `Erro de conexão: ${errorMessage}`,
        },
      ];

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: "error",
          result: errorMessage,
          logs: errorLogs,
        });
        return next;
      });

      console.error(`[useAgentExecution] Error:`, errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [startPolling, stopPolling]);

  const getExecutionStatus = useCallback(
    (cardId: string): ExecutionStatus | undefined => {
      return executions.get(cardId);
    },
    [executions]
  );

  const executeTest = useCallback(async (card: Card): Promise<ExecuteImplementResult> => {
    if (!card.specPath) {
      console.error("[useAgentExecution] Card does not have a specPath");
      return { success: false, error: "Card não possui um plano associado" };
    }

    console.log(`[useAgentExecution] Starting test-implementation for: ${card.specPath}`);

    const initialLogs: ExecutionLog[] = [
      {
        timestamp: new Date().toISOString(),
        type: "info",
        content: `Iniciando validação do plano: ${card.specPath}`,
      },
    ];

    setExecutions((prev) => {
      const next = new Map(prev);
      next.set(card.id, {
        cardId: card.id,
        status: "running",
        logs: initialLogs,
        startedAt: new Date().toISOString(),
      });
      return next;
    });

    // Start polling for real-time logs
    startPolling(card.id);

    try {
      const response = await fetch(`${API_URL}/api/execute-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cardId: card.id,
          specPath: card.specPath,
        }),
      });

      const result = await response.json();
      const logs: ExecutionLog[] = result.logs || [];

      // Stop polling and update final state
      stopPolling(card.id);

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
          completedAt: new Date().toISOString(),
        });
        return next;
      });

      console.log(`[useAgentExecution] Test-implementation completed:`, result);
      return {
        success: result.success,
        result: result.result,
        error: result.error,
      };
    } catch (error) {
      stopPolling(card.id);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      const errorLogs: ExecutionLog[] = [
        ...initialLogs,
        {
          timestamp: new Date().toISOString(),
          type: "error",
          content: `Erro de conexão: ${errorMessage}`,
        },
      ];

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: "error",
          result: errorMessage,
          logs: errorLogs,
        });
        return next;
      });

      console.error(`[useAgentExecution] Error:`, errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [startPolling, stopPolling]);

  const executeReview = useCallback(async (card: Card): Promise<ExecuteImplementResult> => {
    if (!card.specPath) {
      console.error("[useAgentExecution] Card does not have a specPath");
      return { success: false, error: "Card não possui um plano associado" };
    }

    console.log(`[useAgentExecution] Starting review for: ${card.specPath}`);

    const initialLogs: ExecutionLog[] = [
      {
        timestamp: new Date().toISOString(),
        type: "info",
        content: `Iniciando revisão do plano: ${card.specPath}`,
      },
    ];

    setExecutions((prev) => {
      const next = new Map(prev);
      next.set(card.id, {
        cardId: card.id,
        status: "running",
        logs: initialLogs,
        startedAt: new Date().toISOString(),
      });
      return next;
    });

    // Start polling for real-time logs
    startPolling(card.id);

    try {
      const response = await fetch(`${API_URL}/api/execute-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cardId: card.id,
          specPath: card.specPath,
        }),
      });

      const result = await response.json();
      const logs: ExecutionLog[] = result.logs || [];

      // Stop polling and update final state
      stopPolling(card.id);

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
          completedAt: new Date().toISOString(),
        });
        return next;
      });

      console.log(`[useAgentExecution] Review completed:`, result);
      return {
        success: result.success,
        result: result.result,
        error: result.error,
      };
    } catch (error) {
      stopPolling(card.id);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      const errorLogs: ExecutionLog[] = [
        ...initialLogs,
        {
          timestamp: new Date().toISOString(),
          type: "error",
          content: `Erro de conexão: ${errorMessage}`,
        },
      ];

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: "error",
          result: errorMessage,
          logs: errorLogs,
        });
        return next;
      });

      console.error(`[useAgentExecution] Error:`, errorMessage);
      return { success: false, error: errorMessage };
    }
  }, [startPolling, stopPolling]);

  const clearExecution = useCallback((cardId: string) => {
    stopPolling(cardId);
    setExecutions((prev) => {
      const next = new Map(prev);
      next.delete(cardId);
      return next;
    });
  }, [stopPolling]);

  return {
    executions,
    executePlan,
    executeImplement,
    executeTest,
    executeReview,
    getExecutionStatus,
    clearExecution,
  };
}
