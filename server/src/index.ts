import express from "express";
import cors from "cors";
import { executePlan, getExecution, getAllExecutions } from "./agent.js";
import path from "path";

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Get logs for a specific card
app.get("/api/logs/:cardId", (req, res) => {
  const { cardId } = req.params;
  const execution = getExecution(cardId);

  if (!execution) {
    res.status(404).json({
      success: false,
      error: "No execution found for this card",
    });
    return;
  }

  res.json({
    success: true,
    execution,
  });
});

// Get all executions
app.get("/api/executions", (_req, res) => {
  const executions = getAllExecutions();
  res.json({
    success: true,
    executions,
  });
});

// Execute plan endpoint
app.post("/api/execute-plan", async (req, res) => {
  const { cardId, title, description } = req.body;

  // Validate request
  if (!cardId || !title) {
    res.status(400).json({
      success: false,
      error: "Missing required fields: cardId and title are required",
    });
    return;
  }

  console.log(`[Server] Received plan request for card: ${cardId}`);
  console.log(`[Server] Title: ${title}`);
  console.log(`[Server] Description: ${description || "(none)"}`);

  try {
    // Use parent directory as working directory (the main project)
    const cwd = path.resolve(process.cwd(), "..");

    const result = await executePlan(cardId, title, description || "", cwd);

    if (result.success) {
      res.json({
        success: true,
        cardId,
        result: result.result,
        logs: result.logs,
      });
    } else {
      res.status(500).json({
        success: false,
        cardId,
        error: result.error,
        logs: result.logs,
      });
    }
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    console.error(`[Server] Error: ${errorMessage}`);
    res.status(500).json({
      success: false,
      cardId,
      error: errorMessage,
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`[Server] Agent server running on http://localhost:${PORT}`);
  console.log(`[Server] Endpoints:`);
  console.log(`  - GET  /health`);
  console.log(`  - GET  /api/logs/:cardId`);
  console.log(`  - GET  /api/executions`);
  console.log(`  - POST /api/execute-plan`);
});
