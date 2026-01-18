/**
 * Types for Live Spectator System
 */

// ============================================================================
// Status
// ============================================================================

export interface LiveStatus {
  isWorking: boolean;
  currentStage: 'planning' | 'implementing' | 'testing' | 'review' | null;
  currentCard: LiveCard | null;
  progress: number | null;
  spectatorCount: number;
}

// ============================================================================
// Cards
// ============================================================================

export interface LiveCard {
  id: string;
  title: string;
  description?: string;
  columnId: string;
  createdAt: string;
}

export type LiveColumnId = 'backlog' | 'planning' | 'implementing' | 'testing' | 'review' | 'done';

export interface LiveKanban {
  columns: Record<LiveColumnId, LiveCard[]>;
  totalCards: number;
}

// ============================================================================
// Voting
// ============================================================================

export interface VotingOption {
  id: string;
  title: string;
  description?: string;
  category?: string;
  voteCount: number;
}

export interface VotingState {
  isActive: boolean;
  roundId?: string;
  options: VotingOption[];
  endsAt?: string;
  timeRemainingSeconds?: number;
}

// ============================================================================
// Projects
// ============================================================================

export interface CompletedProject {
  id: string;
  title: string;
  description?: string;
  category?: string;
  screenshotUrl?: string;
  previewUrl?: string;
  likeCount: number;
  completedAt: string;
}

// ============================================================================
// WebSocket Messages
// ============================================================================

export type LiveWSMessageType =
  | 'presence_update'
  | 'status_update'
  | 'card_update'
  | 'log_entry'
  | 'voting_started'
  | 'voting_update'
  | 'voting_ended'
  | 'project_liked'
  | 'pong';

export interface WSMessageBase {
  type: LiveWSMessageType;
  timestamp: string;
}

export interface WSPresenceUpdate extends WSMessageBase {
  type: 'presence_update';
  spectatorCount: number;
}

export interface WSStatusUpdate extends WSMessageBase {
  type: 'status_update';
  isWorking: boolean;
  currentStage?: string;
  currentCard?: LiveCard;
  progress?: number;
}

export interface WSCardUpdate extends WSMessageBase {
  type: 'card_update';
  action: 'moved' | 'created' | 'updated';
  card: LiveCard;
  fromColumn?: string;
  toColumn?: string;
}

export interface WSLogEntry extends WSMessageBase {
  type: 'log_entry';
  content: string;
  logType?: 'info' | 'success' | 'error' | 'warning';
}

export interface WSVotingStarted extends WSMessageBase {
  type: 'voting_started';
  roundId: string;
  options: VotingOption[];
  endsAt: string;
  durationSeconds: number;
}

export interface WSVotingUpdate extends WSMessageBase {
  type: 'voting_update';
  votes: Record<string, number>;
}

export interface WSVotingEnded extends WSMessageBase {
  type: 'voting_ended';
  roundId: string;
  winner: VotingOption | null;
  results: VotingOption[];
}

export interface WSProjectLiked extends WSMessageBase {
  type: 'project_liked';
  projectId: string;
  likeCount: number;
}

export type LiveWSMessage =
  | WSPresenceUpdate
  | WSStatusUpdate
  | WSCardUpdate
  | WSLogEntry
  | WSVotingStarted
  | WSVotingUpdate
  | WSVotingEnded
  | WSProjectLiked;

// ============================================================================
// Live State
// ============================================================================

export interface LiveState {
  status: LiveStatus;
  kanban: LiveKanban;
  voting: VotingState;
  logs: WSLogEntry[];
  projects: CompletedProject[];
}
