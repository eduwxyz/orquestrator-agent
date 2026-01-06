import React from 'react';
import type { DiffStats } from '../../types';
import { useDiffAnimation } from '../../hooks/useDiffAnimation';
import styles from './DiffVisualization.module.css';

interface DiffVisualizationProps {
  diffStats: DiffStats | null | undefined;
  isAnimating?: boolean;
}

export function DiffVisualization({ diffStats, isAnimating = true }: DiffVisualizationProps) {
  const { isFrameVisible } = useDiffAnimation(isAnimating ? diffStats : null);

  if (!diffStats) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
              <circle cx="40" cy="40" r="38" stroke="currentColor" strokeWidth="2" strokeDasharray="4 4" opacity="0.3" />
              <path d="M40 20 L40 60 M20 40 L60 40" stroke="currentColor" strokeWidth="2" opacity="0.5" />
            </svg>
          </div>
          <h3 className={styles.emptyTitle}>No Changes Detected</h3>
          <p className={styles.emptyDescription}>
            Code changes will appear here when this card moves to review or done
          </p>
        </div>
      </div>
    );
  }

  const hasFiles = diffStats.filesAdded.length > 0 ||
                   diffStats.filesModified.length > 0 ||
                   diffStats.filesRemoved.length > 0;

  return (
    <div className={styles.container}>
      {/* Holographic grid background */}
      <div className={styles.gridBackground} />

      {/* Floating particles */}
      <div className={styles.particles}>
        {[...Array(12)].map((_, i) => (
          <div key={i} className={styles.particle} style={{
            '--particle-delay': `${i * 0.4}s`,
            '--particle-x': `${Math.random() * 100}%`,
            '--particle-duration': `${3 + Math.random() * 4}s`
          } as React.CSSProperties} />
        ))}
      </div>

      {/* Header with stats overview */}
      <div className={styles.header}>
        <div className={styles.headerGlow} />
        <h2 className={styles.title}>
          <span className={styles.titleIcon}>⚡</span>
          Code Analysis
        </h2>
        <div className={styles.branch}>
          {diffStats.branchName && (
            <>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z"/>
              </svg>
              {diffStats.branchName}
            </>
          )}
        </div>
      </div>

      {/* Main stats display */}
      <div className={styles.statsGrid}>
        {/* Total changes card */}
        <div
          className={`${styles.statCard} ${styles.statCardTotal} ${isFrameVisible('line_stats') ? styles.visible : ''}`}
          style={{ '--card-index': 0 } as React.CSSProperties}
        >
          <div className={styles.statCardGlow} />
          <div className={styles.statValue}>{diffStats.totalChanges.toLocaleString()}</div>
          <div className={styles.statLabel}>Total Changes</div>
          <div className={styles.scanLine} />
        </div>

        {/* Lines added card */}
        <div
          className={`${styles.statCard} ${styles.statCardAdded} ${isFrameVisible('line_stats') ? styles.visible : ''}`}
          style={{ '--card-index': 1 } as React.CSSProperties}
        >
          <div className={styles.statCardGlow} />
          <div className={styles.statIcon}>+</div>
          <div className={styles.statValue}>
            {isFrameVisible('line_stats') && (
              <CountUp end={diffStats.linesAdded} duration={1200} />
            )}
          </div>
          <div className={styles.statLabel}>Lines Added</div>
        </div>

        {/* Lines removed card */}
        <div
          className={`${styles.statCard} ${styles.statCardRemoved} ${isFrameVisible('line_stats') ? styles.visible : ''}`}
          style={{ '--card-index': 2 } as React.CSSProperties}
        >
          <div className={styles.statCardGlow} />
          <div className={styles.statIcon}>−</div>
          <div className={styles.statValue}>
            {isFrameVisible('line_stats') && (
              <CountUp end={diffStats.linesRemoved} duration={1200} />
            )}
          </div>
          <div className={styles.statLabel}>Lines Removed</div>
        </div>
      </div>

      {/* File changes section */}
      {hasFiles && (
        <div className={styles.filesSection}>
          <h3 className={styles.filesTitle}>
            <span className={styles.filesTitleLine} />
            Modified Files
            <span className={styles.filesTitleLine} />
          </h3>

          {/* Added files */}
          {diffStats.filesAdded.length > 0 && (
            <FileGroup
              title="Added"
              files={diffStats.filesAdded}
              icon="+"
              variant="added"
              visible={isFrameVisible('files_added')}
            />
          )}

          {/* Modified files */}
          {diffStats.filesModified.length > 0 && (
            <FileGroup
              title="Modified"
              files={diffStats.filesModified}
              icon="~"
              variant="modified"
              visible={isFrameVisible('files_modified')}
            />
          )}

          {/* Removed files */}
          {diffStats.filesRemoved.length > 0 && (
            <FileGroup
              title="Removed"
              files={diffStats.filesRemoved}
              icon="−"
              variant="removed"
              visible={isFrameVisible('files_removed')}
            />
          )}
        </div>
      )}

      {/* Timestamp */}
      {diffStats.capturedAt && (
        <div className={styles.timestamp}>
          Captured {new Date(diffStats.capturedAt).toLocaleString()}
        </div>
      )}
    </div>
  );
}

interface FileGroupProps {
  title: string;
  files: string[];
  icon: string;
  variant: 'added' | 'modified' | 'removed';
  visible: boolean;
}

function FileGroup({ title, files, icon, variant, visible }: FileGroupProps) {
  const displayFiles = files.slice(0, 100); // Limit to 100 files
  const hasMore = files.length > 100;

  return (
    <div className={`${styles.fileGroup} ${styles[`fileGroup${variant.charAt(0).toUpperCase() + variant.slice(1)}`]} ${visible ? styles.visible : ''}`}>
      <div className={styles.fileGroupHeader}>
        <span className={styles.fileGroupIcon}>{icon}</span>
        <span className={styles.fileGroupTitle}>{title}</span>
        <span className={styles.fileGroupCount}>{files.length}</span>
      </div>
      <div className={styles.fileList}>
        {displayFiles.map((file, index) => (
          <div
            key={`${file}-${index}`}
            className={styles.fileItem}
            style={{ '--file-index': index } as React.CSSProperties}
          >
            <div className={styles.fileItemGlow} />
            <svg className={styles.fileItemIcon} width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
              <path d="M2 2h6l4 4v6H2V2z M8 2v4h4" stroke="currentColor" fill="none" strokeWidth="1.5"/>
            </svg>
            <span className={styles.fileName}>{file}</span>
          </div>
        ))}
        {hasMore && (
          <div className={styles.fileMore}>
            + {files.length - 100} more files
          </div>
        )}
      </div>
    </div>
  );
}

interface CountUpProps {
  end: number;
  duration: number;
}

function CountUp({ end, duration }: CountUpProps) {
  const [count, setCount] = React.useState(0);

  React.useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const progress = Math.min((currentTime - startTime) / duration, 1);

      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      setCount(Math.floor(easeOutQuart * end));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      } else {
        setCount(end);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [end, duration]);

  return <>{count.toLocaleString()}</>;
}
