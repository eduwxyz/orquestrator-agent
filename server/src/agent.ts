import { spawn } from "child_process";

export interface ExecutionLog {
  timestamp: string;
  type: "info" | "tool" | "text" | "error" | "result";
  content: string;
}

export interface ExecutionRecord {
  cardId: string;
  startedAt: string;
  completedAt?: string;
  status: "running" | "success" | "error";
  logs: ExecutionLog[];
  result?: string;
}

export interface PlanResult {
  success: boolean;
  result?: string;
  error?: string;
  logs: ExecutionLog[];
}

// Store executions in memory
const executions = new Map<string, ExecutionRecord>();

export function getExecution(cardId: string): ExecutionRecord | undefined {
  return executions.get(cardId);
}

export function getAllExecutions(): ExecutionRecord[] {
  return Array.from(executions.values());
}

function addLog(
  record: ExecutionRecord,
  type: ExecutionLog["type"],
  content: string
) {
  const log: ExecutionLog = {
    timestamp: new Date().toISOString(),
    type,
    content,
  };
  record.logs.push(log);
  console.log(`[Agent] [${type.toUpperCase()}] ${content}`);
}

export async function executePlan(
  cardId: string,
  title: string,
  description: string,
  cwd: string
): Promise<PlanResult> {
  const prompt = `/plan ${title}: ${description}`;

  // Initialize execution record
  const record: ExecutionRecord = {
    cardId,
    startedAt: new Date().toISOString(),
    status: "running",
    logs: [],
  };
  executions.set(cardId, record);

  addLog(record, "info", `Starting plan execution for: ${title}`);
  addLog(record, "info", `Working directory: ${cwd}`);
  addLog(record, "info", `Prompt: ${prompt}`);

  return new Promise((resolve) => {
    const claude = spawn("claude", ["-p", prompt, "--output-format", "stream-json"], {
      cwd,
      shell: true,
      env: { ...process.env },
    });

    let result = "";

    claude.stdout.on("data", (data: Buffer) => {
      const lines = data.toString().split("\n").filter(Boolean);

      for (const line of lines) {
        try {
          const message = JSON.parse(line);

          if (message.type === "assistant") {
            // Handle assistant messages with content blocks
            if (message.message?.content) {
              for (const block of message.message.content) {
                if (block.type === "text") {
                  addLog(record, "text", block.text);
                  result += block.text + "\n";
                } else if (block.type === "tool_use") {
                  addLog(record, "tool", `Using tool: ${block.name}`);
                }
              }
            }
          } else if (message.type === "result") {
            if (message.result) {
              result = message.result;
              addLog(record, "result", message.result);
            }
          } else if (message.type === "system") {
            addLog(record, "info", `System: ${message.subtype || "init"}`);
          }
        } catch {
          // Not JSON, log as raw text
          const text = line.trim();
          if (text) {
            addLog(record, "text", text);
            result += text + "\n";
          }
        }
      }
    });

    claude.stderr.on("data", (data: Buffer) => {
      const text = data.toString().trim();
      if (text) {
        addLog(record, "error", text);
      }
    });

    claude.on("close", (code) => {
      record.completedAt = new Date().toISOString();

      if (code === 0) {
        record.status = "success";
        record.result = result;
        addLog(record, "info", "Plan execution completed successfully");
        resolve({ success: true, result, logs: record.logs });
      } else {
        record.status = "error";
        record.result = `Process exited with code ${code}`;
        addLog(record, "error", `Process exited with code ${code}`);
        resolve({ success: false, error: `Process exited with code ${code}`, logs: record.logs });
      }
    });

    claude.on("error", (error) => {
      record.status = "error";
      record.completedAt = new Date().toISOString();
      record.result = error.message;
      addLog(record, "error", `Spawn error: ${error.message}`);
      resolve({ success: false, error: error.message, logs: record.logs });
    });
  });
}
