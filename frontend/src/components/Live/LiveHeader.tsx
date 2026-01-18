import styles from './Live.module.css';

interface LiveHeaderProps {
  spectatorCount: number;
  isConnected: boolean;
}

export function LiveHeader({ spectatorCount, isConnected }: LiveHeaderProps) {
  return (
    <header className={styles.header}>
      <div className={styles.headerLeft}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}>🤖</span>
          <span className={styles.logoText}>AI Live Studio</span>
        </div>
        {!isConnected && (
          <span className={styles.disconnected}>Reconnecting...</span>
        )}
      </div>

      <div className={styles.spectatorCount}>
        <span className={styles.spectatorIcon}>👁</span>
        <span className={styles.spectatorNumber}>{spectatorCount}</span>
        <span className={styles.spectatorLabel}>watching</span>
      </div>
    </header>
  );
}
