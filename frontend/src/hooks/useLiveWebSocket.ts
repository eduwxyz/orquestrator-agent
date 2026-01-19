import { useCallback, useReducer, useEffect } from 'react';
import { useWebSocketBase } from './useWebSocketBase';
import { WS_ENDPOINTS } from '../api/config';
import {
  LiveState,
  LiveWSMessage,
  LiveCard,
  VotingOption,
  WSLogEntry,
  LiveColumnId
} from '../types/live';

// ============================================================================
// State Management
// ============================================================================

type AgentStatus = 'idle' | 'working' | 'error';

interface AgentState {
  status: AgentStatus;
  task: string | null;
}

type LiveAction =
  | { type: 'SET_SPECTATOR_COUNT'; count: number }
  | { type: 'SET_STATUS'; isWorking: boolean; stage?: string; card?: LiveCard; progress?: number }
  | { type: 'CARD_MOVED'; card: LiveCard; fromColumn: string; toColumn: string }
  | { type: 'CARD_CREATED'; card: LiveCard }
  | { type: 'CARD_UPDATED'; card: LiveCard }
  | { type: 'ADD_LOG'; log: WSLogEntry }
  | { type: 'VOTING_STARTED'; roundId: string; options: VotingOption[]; endsAt: string; duration: number }
  | { type: 'VOTING_UPDATE'; votes: Record<string, number> }
  | { type: 'VOTING_ENDED'; winner: VotingOption | null; results: VotingOption[] }
  | { type: 'PROJECT_LIKED'; projectId: string; likeCount: number }
  | { type: 'DECREMENT_VOTING_TIME' }
  | { type: 'AGENT_STATUS'; agentId: string; status: AgentStatus; task: string | null };

const initialState: LiveState & { agents: Record<string, AgentState> } = {
  status: {
    isWorking: false,
    currentStage: null,
    currentCard: null,
    progress: null,
    spectatorCount: 0,
  },
  kanban: {
    columns: {
      backlog: [],
      plan: [],
      implement: [],
      test: [],
      review: [],
      done: [],
    },
    totalCards: 0,
  },
  voting: {
    isActive: false,
    options: [],
  },
  logs: [],
  projects: [],
  agents: {
    orchestrator: { status: 'idle', task: null },
    planner: { status: 'idle', task: null },
    coder: { status: 'idle', task: null },
  },
};

type ExtendedLiveState = LiveState & { agents: Record<string, AgentState> };

function liveReducer(state: ExtendedLiveState, action: LiveAction): ExtendedLiveState {
  switch (action.type) {
    case 'SET_SPECTATOR_COUNT':
      return {
        ...state,
        status: { ...state.status, spectatorCount: action.count },
      };

    case 'SET_STATUS':
      return {
        ...state,
        status: {
          ...state.status,
          isWorking: action.isWorking,
          currentStage: action.stage as LiveState['status']['currentStage'],
          currentCard: action.card || null,
          progress: action.progress ?? null,
        },
      };

    case 'CARD_MOVED': {
      const fromCol = action.fromColumn as LiveColumnId;
      const toCol = action.toColumn as LiveColumnId;
      const newColumns = { ...state.kanban.columns };

      // Safety check - ensure columns exist
      if (!newColumns[fromCol] || !newColumns[toCol]) {
        console.warn(`[LiveWS] Invalid columns: from=${fromCol}, to=${toCol}`);
        return state;
      }

      // Remove from old column
      newColumns[fromCol] = newColumns[fromCol].filter(c => c.id !== action.card.id);

      // Add to new column
      newColumns[toCol] = [...newColumns[toCol], { ...action.card, columnId: toCol }];

      return {
        ...state,
        kanban: { ...state.kanban, columns: newColumns },
      };
    }

    case 'CARD_CREATED': {
      const col = action.card.columnId as LiveColumnId;
      const newColumns = { ...state.kanban.columns };

      // Safety check - ensure column exists
      if (!newColumns[col]) {
        console.warn(`[LiveWS] Invalid column for card creation: ${col}`);
        return state;
      }

      newColumns[col] = [...newColumns[col], action.card];

      return {
        ...state,
        kanban: {
          ...state.kanban,
          columns: newColumns,
          totalCards: state.kanban.totalCards + 1,
        },
      };
    }

    case 'CARD_UPDATED': {
      const col = action.card.columnId as LiveColumnId;
      const newColumns = { ...state.kanban.columns };

      // Safety check - ensure column exists
      if (!newColumns[col]) {
        console.warn(`[LiveWS] Invalid column for card update: ${col}`);
        return state;
      }

      newColumns[col] = newColumns[col].map(c =>
        c.id === action.card.id ? action.card : c
      );

      return {
        ...state,
        kanban: { ...state.kanban, columns: newColumns },
      };
    }

    case 'ADD_LOG':
      return {
        ...state,
        logs: [...state.logs.slice(-99), action.log], // Keep last 100 logs
      };

    case 'VOTING_STARTED':
      return {
        ...state,
        voting: {
          isActive: true,
          roundId: action.roundId,
          options: action.options,
          endsAt: action.endsAt,
          timeRemainingSeconds: action.duration,
        },
      };

    case 'VOTING_UPDATE':
      return {
        ...state,
        voting: {
          ...state.voting,
          options: state.voting.options.map(opt => ({
            ...opt,
            voteCount: action.votes[opt.id] ?? opt.voteCount,
          })),
        },
      };

    case 'VOTING_ENDED':
      return {
        ...state,
        voting: {
          isActive: false,
          options: action.results,
        },
      };

    case 'PROJECT_LIKED':
      return {
        ...state,
        projects: state.projects.map(p =>
          p.id === action.projectId
            ? { ...p, likeCount: action.likeCount }
            : p
        ),
      };

    case 'DECREMENT_VOTING_TIME':
      if (!state.voting.isActive || !state.voting.timeRemainingSeconds) {
        return state;
      }
      return {
        ...state,
        voting: {
          ...state.voting,
          timeRemainingSeconds: Math.max(0, state.voting.timeRemainingSeconds - 1),
        },
      };

    case 'AGENT_STATUS':
      return {
        ...state,
        agents: {
          ...state.agents,
          [action.agentId]: {
            status: action.status,
            task: action.task,
          },
        },
      };

    default:
      return state;
  }
}

// ============================================================================
// Hook
// ============================================================================

export function useLiveWebSocket() {
  const [state, dispatch] = useReducer(liveReducer, initialState);

  const handleMessage = useCallback((data: unknown) => {
    const message = data as LiveWSMessage;

    switch (message.type) {
      case 'presence_update':
        // Backend sends snake_case, handle both formats
        const count = (message as any).spectator_count ?? (message as any).spectatorCount ?? 0;
        dispatch({ type: 'SET_SPECTATOR_COUNT', count });
        break;

      case 'status_update':
        // Backend sends snake_case
        const msg = message as any;
        dispatch({
          type: 'SET_STATUS',
          isWorking: msg.is_working ?? msg.isWorking ?? false,
          stage: msg.current_stage ?? msg.currentStage,
          card: msg.current_card ?? msg.currentCard,
          progress: msg.progress,
        });
        break;

      case 'card_update':
        // Backend sends snake_case
        const cardMsg = message as any;
        const fromCol = cardMsg.from_column ?? cardMsg.fromColumn;
        const toCol = cardMsg.to_column ?? cardMsg.toColumn;
        if (cardMsg.action === 'moved' && fromCol && toCol) {
          dispatch({
            type: 'CARD_MOVED',
            card: cardMsg.card,
            fromColumn: fromCol,
            toColumn: toCol,
          });
        } else if (cardMsg.action === 'created') {
          dispatch({ type: 'CARD_CREATED', card: cardMsg.card });
        } else if (cardMsg.action === 'updated') {
          dispatch({ type: 'CARD_UPDATED', card: cardMsg.card });
        }
        break;

      case 'log_entry':
        // Backend sends snake_case
        const logMsg = message as any;
        dispatch({
          type: 'ADD_LOG',
          log: {
            type: 'log_entry',
            content: logMsg.content,
            logType: logMsg.log_type ?? logMsg.logType,
            timestamp: logMsg.timestamp,
          } as WSLogEntry,
        });
        break;

      case 'voting_started':
        dispatch({
          type: 'VOTING_STARTED',
          roundId: message.roundId,
          options: message.options,
          endsAt: message.endsAt,
          duration: message.durationSeconds,
        });
        break;

      case 'voting_update':
        dispatch({ type: 'VOTING_UPDATE', votes: message.votes });
        break;

      case 'voting_ended':
        dispatch({
          type: 'VOTING_ENDED',
          winner: message.winner,
          results: message.results,
        });
        break;

      case 'project_liked':
        dispatch({
          type: 'PROJECT_LIKED',
          projectId: message.projectId,
          likeCount: message.likeCount,
        });
        break;

      case 'agent_status':
        const agentMsg = message as any;
        dispatch({
          type: 'AGENT_STATUS',
          agentId: agentMsg.agent_id ?? agentMsg.agentId,
          status: agentMsg.status,
          task: agentMsg.task,
        });
        break;
    }
  }, []);

  const { isConnected, status, send, reconnect } = useWebSocketBase({
    url: WS_ENDPOINTS.live,
    enabled: true,
    onMessage: handleMessage,
    name: 'LiveWS',
    maxReconnectAttempts: 9999, // Praticamente infinito
    baseReconnectDelay: 500,    // Começar com 500ms
    maxReconnectDelay: 10000,   // Máximo 10s entre tentativas
    heartbeatInterval: 15000,   // Heartbeat a cada 15s
    pongTimeout: 5000,          // Timeout pong em 5s
  });

  // Voting countdown timer
  useEffect(() => {
    if (!state.voting.isActive) return;

    const timer = setInterval(() => {
      dispatch({ type: 'DECREMENT_VOTING_TIME' });
    }, 1000);

    return () => clearInterval(timer);
  }, [state.voting.isActive]);

  return {
    state,
    isConnected,
    connectionStatus: status,
    reconnect,
    send,
  };
}
