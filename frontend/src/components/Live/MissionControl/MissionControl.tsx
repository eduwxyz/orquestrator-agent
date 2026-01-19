import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { LiveState } from '../../../types/live';
import { VotingModal } from '../VotingModal';
import { AutoReactions } from './AutoReactions';
import styles from './MissionControl.module.css';

interface AgentState {
  status: 'idle' | 'working' | 'error';
  task: string | null;
}

interface MissionControlProps {
  state: LiveState & { agents?: Record<string, AgentState> };
  isConnected: boolean;
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

export function MissionControl({ state, isConnected }: MissionControlProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [uptime, setUptime] = useState(0);
  const [reactionTrigger, setReactionTrigger] = useState<'success' | 'error' | 'start' | 'idle' | null>(null);
  const lastLogCountRef = useRef(0);
  const wasWorkingRef = useRef(false);

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

  const getEventIcon = (logType?: string) => {
    switch (logType) {
      case 'success': return '✓';
      case 'error': return '✗';
      case 'warning': return '⚠';
      case 'tool': return '⚡';
      case 'result': return '→';
      default: return '•';
    }
  };

  // Calculate stats
  const completedTasks = state.kanban.columns.done?.length || 0;
  const totalTasks = state.kanban.totalCards;
  const inProgress = (state.kanban.columns.implement?.length || 0) +
                     (state.kanban.columns.test?.length || 0);

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

        {/* Event Feed */}
        <section className={styles.eventSection}>
          <div className={styles.eventFeed}>
            <div className={styles.panelTitle}>
              <span className={styles.panelTitleIcon}>📋</span>
              Event Log
            </div>
            <div className={styles.eventList}>
              {state.logs.slice(-10).reverse().map((log, idx) => (
                <div
                  key={`event-${log.timestamp}-${idx}`}
                  className={`${styles.eventItem} ${getLogTypeClass(log.logType)}`}
                >
                  <span className={styles.eventIcon}>{getEventIcon(log.logType)}</span>
                  <div className={styles.eventContent}>
                    <div className={styles.eventMessage}>{log.content}</div>
                    <div className={styles.eventTime}>
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              {state.logs.length === 0 && (
                <div className={styles.eventItem}>
                  <span className={styles.eventIcon}>•</span>
                  <div className={styles.eventContent}>
                    <div className={styles.eventMessage}>System initialized. Waiting for events...</div>
                    <div className={styles.eventTime}>{new Date().toLocaleTimeString()}</div>
                  </div>
                </div>
              )}
            </div>
          </div>

        </section>
      </main>

      {/* Voting Modal - Full Screen Overlay */}
      <VotingModal voting={state.voting} sessionId={sessionId} />
    </div>
  );
}
