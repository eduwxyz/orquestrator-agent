import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { LiveState } from '../../../types/live';
import { VotingModal } from '../VotingModal';
import { AutoReactions } from './AutoReactions';
import { SnakeGame } from './SnakeGame';
import { GameRanking, RankingEntry } from './GameRanking';
import { ProjectGallery } from './ProjectGallery';
import styles from './MissionControl.module.css';

interface AgentState {
  status: 'idle' | 'working' | 'error';
  task: string | null;
}

interface MissionControlProps {
  state: LiveState & { agents?: Record<string, AgentState> };
  isConnected: boolean;
  rankingUpdate?: { entry: RankingEntry; rank: number } | null;
}

// Agent display configuration
interface AgentDisplay {
  id: string;
  name: string;
  role: string;
  avatar: string;
  stateKey: string;
}

const AGENT_CONFIG: AgentDisplay[] = [
  { id: '1', name: 'ORCHESTRATOR', role: 'Coordinator', avatar: '🤖', stateKey: 'orchestrator' },
  { id: '2', name: 'PLANNER', role: 'Planner', avatar: '📋', stateKey: 'planner' },
  { id: '3', name: 'CODER', role: 'Coder', avatar: '💻', stateKey: 'coder' },
];

export function MissionControl({ state, isConnected, rankingUpdate }: MissionControlProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [uptime, setUptime] = useState(0);
  const [reactionTrigger, setReactionTrigger] = useState<'success' | 'error' | 'start' | 'idle' | null>(null);
  const lastLogCountRef = useRef(0);
  const wasWorkingRef = useRef(false);

  // Game state
  const [ranking, setRanking] = useState<RankingEntry[]>([]);
  const [playerName, setPlayerName] = useState<string>(() => {
    return localStorage.getItem('snake_player_name') || '';
  });
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [pendingScore, setPendingScore] = useState<number | null>(null);
  const [inputName, setInputName] = useState('');
  const [lastSaveResult, setLastSaveResult] = useState<{ success: boolean; rank?: number; message?: string } | null>(null);
  const [isChangingName, setIsChangingName] = useState(false);
  const [showGallery, setShowGallery] = useState(false);

  // Build agents from real state
  const agents = useMemo(() => {
    const agentStates = state.agents || {
      orchestrator: { status: 'idle' as const, task: null },
      planner: { status: 'idle' as const, task: null },
      coder: { status: 'idle' as const, task: null },
    };

    return AGENT_CONFIG.map(config => ({
      id: config.id,
      name: config.name,
      role: config.role,
      avatar: config.avatar,
      status: agentStates[config.stateKey]?.status || 'idle',
      task: agentStates[config.stateKey]?.task || undefined,
      progress: state.status.progress || 0,
    }));
  }, [state.agents, state.status.progress]);

  // Session ID for voting
  const [sessionId] = useState(() => {
    const stored = sessionStorage.getItem('live_session_id');
    if (stored) return stored;
    const newId = uuidv4();
    sessionStorage.setItem('live_session_id', newId);
    return newId;
  });

  // Trigger reaction helper
  const triggerReaction = useCallback((type: 'success' | 'error' | 'start' | 'idle') => {
    setReactionTrigger(type);
    // Reset after a short delay to allow re-triggering
    setTimeout(() => setReactionTrigger(null), 100);
  }, []);

  // Detect events and trigger reactions
  useEffect(() => {
    const logs = state.logs;
    const newLogs = logs.slice(lastLogCountRef.current);
    lastLogCountRef.current = logs.length;

    // Check new logs for success/error
    for (const log of newLogs) {
      if (log.logType === 'success') {
        triggerReaction('success');
        break;
      } else if (log.logType === 'error') {
        triggerReaction('error');
        break;
      }
    }
  }, [state.logs, triggerReaction]);

  // Detect work start/stop
  useEffect(() => {
    if (state.status.isWorking && !wasWorkingRef.current) {
      // Just started working
      triggerReaction('start');
    }
    wasWorkingRef.current = state.status.isWorking;
  }, [state.status.isWorking, triggerReaction]);


  // Uptime counter
  useEffect(() => {
    const interval = setInterval(() => {
      setUptime(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [state.logs.length]);

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const getLogTypeClass = (logType?: string) => {
    switch (logType) {
      case 'success': return styles.success;
      case 'error': return styles.error;
      case 'warning': return styles.warning;
      case 'tool': return styles.tool;
      case 'result': return styles.result;
      case 'text': return styles.text;
      default: return styles.info;
    }
  };

  // Calculate stats
  const completedTasks = state.kanban.columns.done?.length || 0;
  const totalTasks = state.kanban.totalCards;
  const inProgress = (state.kanban.columns.implement?.length || 0) +
                     (state.kanban.columns.test?.length || 0);

  // Fetch ranking
  const fetchRanking = useCallback(async () => {
    try {
      const response = await fetch('/api/live/game/ranking?game_type=snake&limit=10');
      if (response.ok) {
        const data = await response.json();
        setRanking(data.ranking || []);
      }
    } catch (error) {
      console.error('Failed to fetch ranking:', error);
    }
  }, []);

  // Submit score
  const submitScore = useCallback(async (score: number, name: string) => {
    console.log('[SnakeGame] Submitting score:', { name, score, sessionId });
    try {
      const response = await fetch('/api/live/game/score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player_name: name,
          score,
          game_type: 'snake',
          session_id: sessionId,
        }),
      });
      const data = await response.json();
      console.log('[SnakeGame] Score response:', response.status, data);

      if (response.ok) {
        setLastSaveResult({ success: true, rank: data.rank });
        // Refresh ranking after submitting
        fetchRanking();
      } else {
        setLastSaveResult({ success: false, message: data.detail || 'Erro ao salvar' });
      }

      // Clear toast after 3s
      setTimeout(() => setLastSaveResult(null), 3000);
    } catch (error) {
      console.error('[SnakeGame] Failed to submit score:', error);
      setLastSaveResult({ success: false, message: 'Erro de conexão' });
      setTimeout(() => setLastSaveResult(null), 3000);
    }
  }, [sessionId, fetchRanking]);

  // Handle game over
  const handleGameOver = useCallback((score: number) => {
    if (score === 0) return; // Don't save zero scores

    if (playerName) {
      submitScore(score, playerName);
    } else {
      setPendingScore(score);
      setShowNamePrompt(true);
    }
  }, [playerName, submitScore]);

  // Handle name submit
  const handleNameSubmit = useCallback((name: string) => {
    const trimmedName = name.trim().slice(0, 15); // Max 15 chars
    console.log('[SnakeGame] handleNameSubmit:', { name, trimmedName, pendingScore, isChangingName });
    if (!trimmedName) return;

    localStorage.setItem('snake_player_name', trimmedName);
    setPlayerName(trimmedName);
    setShowNamePrompt(false);
    setIsChangingName(false);

    if (pendingScore !== null && !isChangingName) {
      submitScore(pendingScore, trimmedName);
      setPendingScore(null);
    }
  }, [pendingScore, submitScore, isChangingName]);

  // Handle change name request
  const handleChangeName = useCallback(() => {
    setInputName(playerName);
    setIsChangingName(true);
    setShowNamePrompt(true);
  }, [playerName]);

  // Load ranking on mount
  useEffect(() => {
    fetchRanking();
  }, [fetchRanking]);

  // Poll ranking every 10 seconds
  useEffect(() => {
    const interval = setInterval(fetchRanking, 10000);
    return () => clearInterval(interval);
  }, [fetchRanking]);

  // Handle real-time ranking updates from WebSocket
  useEffect(() => {
    if (rankingUpdate?.entry) {
      // Add new entry to ranking with isNew flag
      setRanking(prev => {
        const newEntry = { ...rankingUpdate.entry, isNew: true };

        // Check if entry already exists
        const existingIndex = prev.findIndex(e => e.id === newEntry.id);
        if (existingIndex >= 0) {
          return prev;
        }

        // Insert at correct position based on rank
        const newRanking = [...prev];
        const insertIndex = rankingUpdate.rank - 1;
        newRanking.splice(insertIndex, 0, newEntry);

        // Keep only top 10
        return newRanking.slice(0, 10);
      });
    }
  }, [rankingUpdate]);

  return (
    <div className={styles.container}>
      {/* Auto Reactions Overlay */}
      <AutoReactions trigger={reactionTrigger} />

      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.liveIndicator}>
            <div className={styles.liveDot} />
            <span className={styles.liveText}>LIVE</span>
          </div>
          <span className={styles.title}>ORQUESTRATOR MISSION CONTROL</span>
        </div>

        <div className={styles.headerCenter}>
          <div className={styles.stat}>
            <span className={styles.statIcon}>👁</span>
            <span className={styles.statValue}>{state.status.spectatorCount}</span>
            <span className={styles.statLabel}>Watching</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statIcon}>✓</span>
            <span className={styles.statValue}>{completedTasks}</span>
            <span className={styles.statLabel}>Completed</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statIcon}>⚡</span>
            <span className={styles.statValue}>{inProgress}</span>
            <span className={styles.statLabel}>In Progress</span>
          </div>
        </div>

        <div className={styles.headerRight}>
          <button
            className={styles.galleryButton}
            onClick={() => setShowGallery(true)}
            title="Ver projetos finalizados"
          >
            <span className={styles.galleryIcon}>🏆</span>
            <span className={styles.galleryText}>Projetos</span>
          </button>
          <div className={styles.timer}>{formatUptime(uptime)}</div>
          <div className={`${styles.connectionStatus} ${isConnected ? styles.connected : styles.disconnected}`}>
            <div className={styles.statusDot} />
            <span>{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className={styles.main}>
        {/* Terminal Section */}
        <section className={styles.terminalSection}>
          <div className={styles.terminal}>
            <div className={styles.terminalHeader}>
              <div className={styles.terminalDots}>
                <div className={`${styles.terminalDot} ${styles.red}`} />
                <div className={`${styles.terminalDot} ${styles.yellow}`} />
                <div className={`${styles.terminalDot} ${styles.green}`} />
              </div>
              <span className={styles.terminalTitle}>agent-output — bash</span>
            </div>
            <div className={styles.terminalBody} ref={terminalRef}>
              {state.logs.length === 0 ? (
                <div className={styles.terminalLine}>
                  <span className={styles.terminalPrompt}>$</span>
                  <span className={styles.terminalContent}>Waiting for agent activity...</span>
                  <span className={styles.terminalCursor} />
                </div>
              ) : (
                <>
                  {state.logs.slice(-50).map((log, idx) => (
                    <div key={`${log.timestamp}-${idx}`} className={styles.terminalLine}>
                      <span className={styles.terminalPrompt}>
                        {log.logType === 'tool' ? '⚡' : log.logType === 'result' ? '→' : '$'}
                      </span>
                      <span className={`${styles.terminalContent} ${getLogTypeClass(log.logType)}`}>
                        {log.content}
                      </span>
                    </div>
                  ))}
                  <div className={styles.terminalLine}>
                    <span className={styles.terminalPrompt}>$</span>
                    <span className={styles.terminalCursor} />
                  </div>
                </>
              )}
            </div>
          </div>
        </section>

        {/* Agents Panel */}
        <section className={styles.agentsSection}>
          {/* Activity Indicator */}
          <div className={`${styles.activityIndicator} ${!state.status.isWorking ? styles.idle : ''}`}>
            <span className={styles.activityIcon}>
              {state.status.isWorking ? '⚙️' : '💤'}
            </span>
            <span className={styles.activityText}>
              {state.status.isWorking ? 'AI is working...' : 'Waiting for tasks...'}
            </span>
            {state.status.isWorking && (
              <div className={styles.audioVisualizer}>
                {[...Array(8)].map((_, i) => (
                  <div key={i} className={styles.audioBar} />
                ))}
              </div>
            )}
          </div>

          {/* Current Task */}
          {state.status.currentCard && (
            <div className={styles.currentTask}>
              <div className={styles.currentTaskHeader}>
                <span className={styles.currentTaskLabel}>Current Task</span>
                <span className={styles.currentTaskStage}>
                  {state.status.currentStage || 'Processing'}
                </span>
              </div>
              <div className={styles.currentTaskTitle}>
                {state.status.currentCard.title}
              </div>
              <div className={styles.currentTaskProgress}>
                <div className={styles.currentTaskProgressBar}>
                  <div
                    className={styles.currentTaskProgressFill}
                    style={{ width: `${state.status.progress || 0}%` }}
                  />
                </div>
                <span className={styles.currentTaskPercent}>
                  {state.status.progress || 0}%
                </span>
              </div>
            </div>
          )}

          <div className={styles.panelTitle}>
            <span className={styles.panelTitleIcon}>🤖</span>
            Active Agents
          </div>

          {agents.map(agent => (
            <div
              key={agent.id}
              className={`${styles.agentCard} ${agent.status === 'working' ? styles.active : ''} ${agent.status === 'error' ? styles.error : ''}`}
            >
              <div className={styles.agentHeader}>
                <div className={styles.agentAvatar}>{agent.avatar}</div>
                <div className={styles.agentInfo}>
                  <div className={styles.agentName}>{agent.name}</div>
                  <div className={styles.agentRole}>{agent.role}</div>
                </div>
                <div className={`${styles.agentStatus} ${styles[agent.status]}`}>
                  {agent.status.toUpperCase()}
                </div>
              </div>

              {agent.task && (
                <div className={styles.agentTask}>{agent.task}</div>
              )}

              {agent.status === 'working' && (
                <div className={styles.agentProgress}>
                  <div className={styles.progressHeader}>
                    <span>Progress</span>
                    <span>{agent.progress}%</span>
                  </div>
                  <div className={styles.progressBar}>
                    <div
                      className={styles.progressFill}
                      style={{ width: `${agent.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Mini Kanban */}
          <div className={styles.kanbanMini}>
            <div className={styles.kanbanMiniTitle}>
              <span>📊</span>
              Pipeline Status
            </div>
            <div className={styles.kanbanMiniColumns}>
              {(['backlog', 'plan', 'implement', 'test', 'review', 'done'] as const).map(col => {
                const count = state.kanban.columns[col]?.length || 0;
                const isActive = state.status.currentStage === col ||
                  (col === 'implement' && state.status.currentStage === 'implementing') ||
                  (col === 'test' && state.status.currentStage === 'testing') ||
                  (col === 'review' && state.status.currentStage === 'review') ||
                  (col === 'plan' && state.status.currentStage === 'planning');
                const isDone = col === 'done';
                return (
                  <div
                    key={col}
                    className={`${styles.kanbanMiniColumn} ${isActive ? styles.active : ''} ${isDone && count > 0 ? styles.done : ''}`}
                  >
                    <div className={styles.kanbanMiniColumnHeader}>
                      {col.slice(0, 4).toUpperCase()}
                    </div>
                    <div className={styles.kanbanMiniColumnCount}>{count}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Status Cards */}
          <div className={styles.statusCards}>
            <div className={styles.statusCard}>
              <div className={styles.statusCardValue}>{totalTasks}</div>
              <div className={styles.statusCardLabel}>Total Tasks</div>
            </div>
            <div className={`${styles.statusCard} ${styles.highlight}`}>
              <div className={styles.statusCardValue}>
                {totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0}%
              </div>
              <div className={styles.statusCardLabel}>Complete</div>
            </div>
          </div>
        </section>

        {/* Game Section */}
        <section className={styles.gameSection}>
          <SnakeGame
            onGameOver={handleGameOver}
            playerName={playerName}
            onChangeName={handleChangeName}
            lastSaveResult={lastSaveResult}
          />
          <GameRanking
            ranking={ranking}
            currentPlayerName={playerName}
          />
        </section>

        {/* Name Prompt Modal */}
        {showNamePrompt && (
          <div className={styles.namePromptOverlay}>
            <div className={styles.namePromptModal}>
              <div className={styles.namePromptTitle}>
                {isChangingName ? '✏️ Trocar Nome' : '🏆 Salvar Score!'}
              </div>
              {!isChangingName && pendingScore !== null && (
                <div className={styles.namePromptScore}>Score: {pendingScore}</div>
              )}
              <input
                type="text"
                placeholder="Digite seu nome..."
                maxLength={15}
                className={styles.namePromptInput}
                autoFocus
                value={inputName}
                onChange={(e) => setInputName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && inputName.trim()) {
                    handleNameSubmit(inputName);
                    setInputName('');
                  }
                  if (e.key === 'Escape') {
                    setShowNamePrompt(false);
                    setIsChangingName(false);
                    setInputName('');
                  }
                }}
              />
              <div className={styles.namePromptButtons}>
                <button
                  className={styles.namePromptButton}
                  onClick={() => {
                    if (inputName.trim()) {
                      handleNameSubmit(inputName);
                      setInputName('');
                    }
                  }}
                >
                  Salvar
                </button>
                {isChangingName && (
                  <button
                    className={styles.namePromptCancelButton}
                    onClick={() => {
                      setShowNamePrompt(false);
                      setIsChangingName(false);
                      setInputName('');
                    }}
                  >
                    Cancelar
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Voting Modal - Full Screen Overlay */}
      <VotingModal voting={state.voting} sessionId={sessionId} />

      {/* Project Gallery Modal */}
      <ProjectGallery isOpen={showGallery} onClose={() => setShowGallery(false)} />
    </div>
  );
}
