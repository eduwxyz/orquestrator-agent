import { useState, useEffect } from 'react';
import { API_CONFIG } from '../../api/config';
import styles from './LiveModeControl.module.css';

export function LiveModeControl() {
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check initial status
  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/live/admin/live-mode`);
      const data = await response.json();
      setIsActive(data.active);
    } catch (err) {
      console.error('Failed to check live mode status:', err);
    }
  };

  const handleStart = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/live/admin/live-mode/start`, {
        method: 'POST',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to start');
      }

      setIsActive(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start live mode');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/live/admin/live-mode/stop`, {
        method: 'POST',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to stop');
      }

      setIsActive(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop live mode');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.icon}>📺</span>
        <span className={styles.title}>Live Mode</span>
        <span className={`${styles.status} ${isActive ? styles.active : styles.inactive}`}>
          {isActive ? 'ON AIR' : 'OFF'}
        </span>
      </div>

      <div className={styles.controls}>
        {!isActive ? (
          <button
            className={styles.startButton}
            onClick={handleStart}
            disabled={isLoading}
          >
            {isLoading ? 'Starting...' : '▶ Start Live'}
          </button>
        ) : (
          <button
            className={styles.stopButton}
            onClick={handleStop}
            disabled={isLoading}
          >
            {isLoading ? 'Stopping...' : '⏹ Stop Live'}
          </button>
        )}
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {isActive && (
        <div className={styles.info}>
          AI is creating projects for spectators!
          <a
            href="/live"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.link}
          >
            Open /live →
          </a>
        </div>
      )}
    </div>
  );
}
