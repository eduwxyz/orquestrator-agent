import { useRef, useEffect } from 'react';
import { WSLogEntry } from '../../types/live';
import styles from './Live.module.css';

interface LiveLogsProps {
  logs: WSLogEntry[];
}

const LOG_TYPE_COLORS: Record<string, string> = {
  info: '#64748b',
  success: '#22c55e',
  error: '#ef4444',
  warning: '#f59e0b',
};

export function LiveLogs({ logs }: LiveLogsProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs.length]);

  return (
    <div className={styles.logsPanel}>
      <h3 className={styles.sectionTitle}>Live Logs</h3>

      <div className={styles.logsContainer} ref={containerRef}>
        {logs.length === 0 ? (
          <div className={styles.noLogs}>No logs yet...</div>
        ) : (
          logs.map((log, index) => (
            <div
              key={`${log.timestamp}-${index}`}
              className={styles.logEntry}
              style={{ borderLeftColor: LOG_TYPE_COLORS[log.logType || 'info'] }}
            >
              <span className={styles.logTime}>
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={styles.logContent}>{log.content}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
