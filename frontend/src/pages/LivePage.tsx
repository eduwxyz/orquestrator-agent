import { useEffect, useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useLiveWebSocket } from '../hooks/useLiveWebSocket';
import {
  LiveHeader,
  LiveStatusPanel,
  LiveKanbanBoard,
  LiveLogs,
  VotingPanel,
  ProjectGallery
} from '../components/Live';
import styles from './LivePage.module.css';

export function LivePage() {
  // Generate or retrieve session ID
  const [sessionId] = useState(() => {
    const stored = sessionStorage.getItem('live_session_id');
    if (stored) return stored;
    const newId = uuidv4();
    sessionStorage.setItem('live_session_id', newId);
    return newId;
  });

  // Connect to live WebSocket
  const { state, isConnected } = useLiveWebSocket();

  // Update page title with spectator count
  useEffect(() => {
    document.title = `AI Live Studio (${state.status.spectatorCount} watching)`;
    return () => {
      document.title = 'AI Live Studio';
    };
  }, [state.status.spectatorCount]);

  return (
    <div className={styles.container}>
      <LiveHeader
        spectatorCount={state.status.spectatorCount}
        isConnected={isConnected}
      />

      <main className={styles.main}>
        <div className={styles.grid}>
          {/* Left Column: Status + Logs */}
          <div className={styles.leftColumn}>
            <LiveStatusPanel status={state.status} />
            <LiveLogs logs={state.logs} />
          </div>

          {/* Center: Kanban Board */}
          <div className={styles.centerColumn}>
            <LiveKanbanBoard kanban={state.kanban} />
          </div>
        </div>

        {/* Voting Section */}
        <div className={styles.votingSection}>
          <VotingPanel voting={state.voting} sessionId={sessionId} />
        </div>

        {/* Gallery Section */}
        <div className={styles.gallerySection}>
          <ProjectGallery sessionId={sessionId} />
        </div>
      </main>

      <footer className={styles.footer}>
        <span>Powered by AI</span>
        <span className={styles.separator}>|</span>
        <span>Watch the AI create projects autonomously</span>
      </footer>
    </div>
  );
}
