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
  | { type: 'DECREMENT_VOTING_TIME' };

const initialState: LiveState = {
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
      planning: [],
      implementing: [],
      testing: [],
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
};

function liveReducer(state: LiveState, action: LiveAction): LiveState {
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
        dispatch({ type: 'SET_SPECTATOR_COUNT', count: message.spectatorCount });
        break;

      case 'status_update':
        dispatch({
          type: 'SET_STATUS',
          isWorking: message.isWorking,
          stage: message.currentStage,
          card: message.currentCard,
          progress: message.progress,
        });
        break;

      case 'card_update':
        if (message.action === 'moved' && message.fromColumn && message.toColumn) {
          dispatch({
            type: 'CARD_MOVED',
            card: message.card,
            fromColumn: message.fromColumn,
            toColumn: message.toColumn,
          });
        } else if (message.action === 'created') {
          dispatch({ type: 'CARD_CREATED', card: message.card });
        } else if (message.action === 'updated') {
          dispatch({ type: 'CARD_UPDATED', card: message.card });
        }
        break;

      case 'log_entry':
        dispatch({
          type: 'ADD_LOG',
          log: message as WSLogEntry,
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
    }
  }, []);

  const { isConnected, status, send, reconnect } = useWebSocketBase({
    url: WS_ENDPOINTS.live,
    enabled: true,
    onMessage: handleMessage,
    name: 'LiveWS',
    maxReconnectAttempts: 15,
    heartbeatInterval: 30000,
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
