import { useState, useCallback } from "react";
import { Card, ExecutionStatus, ExecutionLog } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3001";

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

export function useAgentExecution() {
  const [executions, setExecutions] = useState<Map<string, ExecutionStatus>>(
    new Map()
  );

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
      });
      return next;
    });

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

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
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
  }, []);

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
      });
      return next;
    });

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

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
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
  }, []);

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
      });
      return next;
    });

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

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
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
  }, []);

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
      });
      return next;
    });

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

      setExecutions((prev) => {
        const next = new Map(prev);
        next.set(card.id, {
          cardId: card.id,
          status: result.success ? "success" : "error",
          result: result.result || result.error,
          logs: logs,
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
  }, []);

  const clearExecution = useCallback((cardId: string) => {
    setExecutions((prev) => {
      const next = new Map(prev);
      next.delete(cardId);
      return next;
    });
  }, []);

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
