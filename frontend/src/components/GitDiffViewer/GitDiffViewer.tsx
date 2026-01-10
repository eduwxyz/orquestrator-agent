import { useState } from 'react';
import type { DiffStats } from '../../types';
import styles from './GitDiffViewer.module.css';

interface GitDiffViewerProps {
  diffStats: DiffStats | null | undefined;
}

interface ParsedLine {
  type: 'header' | 'hunk' | 'added' | 'removed' | 'context' | 'meta';
  content: string;
  lineNumber?: {
    old?: number;
    new?: number;
  };
}

function parseDiffContent(content: string): ParsedLine[] {
  const lines = content.split('\n');
  const parsed: ParsedLine[] = [];

  let oldLineNum = 0;
  let newLineNum = 0;

  for (const line of lines) {
    if (line.startsWith('diff --git')) {
      parsed.push({ type: 'header', content: line });
    } else if (line.startsWith('index ') || line.startsWith('---') || line.startsWith('+++')) {
      parsed.push({ type: 'meta', content: line });
    } else if (line.startsWith('@@')) {
      // Parse hunk header: @@ -start,count +start,count @@
      const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/);
      if (match) {
        oldLineNum = parseInt(match[1], 10);
        newLineNum = parseInt(match[2], 10);
      }
      parsed.push({ type: 'hunk', content: line });
    } else if (line.startsWith('+')) {
      parsed.push({
        type: 'added',
        content: line.slice(1),
        lineNumber: { new: newLineNum++ }
      });
    } else if (line.startsWith('-')) {
      parsed.push({
        type: 'removed',
        content: line.slice(1),
        lineNumber: { old: oldLineNum++ }
      });
    } else if (line.startsWith(' ') || line === '') {
      parsed.push({
        type: 'context',
        content: line.slice(1) || '',
        lineNumber: { old: oldLineNum++, new: newLineNum++ }
      });
    }
  }

  return parsed;
}

function getFileIcon(status: string): string {
  switch (status) {
    case 'added': return '+';
    case 'removed': return '-';
    default: return '~';
  }
}

function getFileName(path: string): string {
  return path.split('/').pop() || path;
}

function getFileDir(path: string): string {
  const parts = path.split('/');
  if (parts.length <= 1) return '';
  return parts.slice(0, -1).join('/') + '/';
}

export function GitDiffViewer({ diffStats }: GitDiffViewerProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [selectedFileIndex, setSelectedFileIndex] = useState<number | null>(null);

  if (!diffStats) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect x="8" y="6" width="32" height="36" rx="2" stroke="currentColor" strokeWidth="2" fill="none"/>
              <path d="M16 18h16M16 24h16M16 30h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <p className={styles.emptyText}>No diff content available</p>
        </div>
      </div>
    );
  }

  const fileDiffs = diffStats.fileDiffs || [];

  if (fileDiffs.length === 0) {
    return (
      <div className={styles.container}>
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect x="8" y="6" width="32" height="36" rx="2" stroke="currentColor" strokeWidth="2" fill="none"/>
              <path d="M16 18h16M16 24h16M16 30h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <p className={styles.emptyText}>No code changes to display</p>
          <p className={styles.emptySubtext}>
            {diffStats.totalChanges > 0
              ? 'Diff content was not captured for this card'
              : 'This card has no file modifications'}
          </p>
        </div>
      </div>
    );
  }

  const toggleFile = (index: number) => {
    const newExpanded = new Set(expandedFiles);
    if (newExpanded.has(String(index))) {
      newExpanded.delete(String(index));
      if (selectedFileIndex === index) {
        setSelectedFileIndex(null);
      }
    } else {
      newExpanded.add(String(index));
      setSelectedFileIndex(index);
    }
    setExpandedFiles(newExpanded);
  };

  const expandAll = () => {
    setExpandedFiles(new Set(fileDiffs.map((_, i) => String(i))));
  };

  const collapseAll = () => {
    setExpandedFiles(new Set());
    setSelectedFileIndex(null);
  };

  return (
    <div className={styles.container}>
      {/* Summary Header */}
      <div className={styles.summary}>
        <div className={styles.summaryStats}>
          <span className={styles.statFiles}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
              <path d="M2 2h6l4 4v6H2V2z M8 2v4h4" stroke="currentColor" fill="none" strokeWidth="1.2"/>
            </svg>
            {fileDiffs.length} {fileDiffs.length === 1 ? 'file' : 'files'}
          </span>
          <span className={styles.statAdded}>+{diffStats.linesAdded}</span>
          <span className={styles.statRemoved}>-{diffStats.linesRemoved}</span>
        </div>
        <div className={styles.summaryActions}>
          <button className={styles.actionBtn} onClick={expandAll}>Expand all</button>
          <button className={styles.actionBtn} onClick={collapseAll}>Collapse all</button>
        </div>
      </div>

      {/* File List */}
      <div className={styles.fileList}>
        {fileDiffs.map((file, index) => {
          const isExpanded = expandedFiles.has(String(index));
          const parsedLines = isExpanded ? parseDiffContent(file.content) : [];

          return (
            <div key={`${file.path}-${index}`} className={styles.fileItem}>
              {/* File Header */}
              <button
                className={`${styles.fileHeader} ${styles[`file${file.status.charAt(0).toUpperCase() + file.status.slice(1)}`]}`}
                onClick={() => toggleFile(index)}
              >
                <span className={styles.fileIcon}>{getFileIcon(file.status)}</span>
                <span className={styles.filePath}>
                  <span className={styles.fileDir}>{getFileDir(file.path)}</span>
                  <span className={styles.fileName}>{getFileName(file.path)}</span>
                </span>
                <span className={styles.fileStatus}>{file.status}</span>
                <span className={styles.expandIcon}>
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 12 12"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    style={{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
                  >
                    <path d="M2 4l4 4 4-4" />
                  </svg>
                </span>
              </button>

              {/* Diff Content */}
              {isExpanded && (
                <div className={styles.diffContent}>
                  <table className={styles.diffTable}>
                    <tbody>
                      {parsedLines.map((line, lineIndex) => (
                        <tr
                          key={lineIndex}
                          className={`${styles.diffLine} ${styles[`line${line.type.charAt(0).toUpperCase() + line.type.slice(1)}`]}`}
                        >
                          {line.type === 'header' || line.type === 'meta' || line.type === 'hunk' ? (
                            <td colSpan={3} className={styles.lineSpecial}>
                              {line.content}
                            </td>
                          ) : (
                            <>
                              <td className={styles.lineNum}>
                                {line.lineNumber?.old ?? ''}
                              </td>
                              <td className={styles.lineNum}>
                                {line.lineNumber?.new ?? ''}
                              </td>
                              <td className={styles.lineCode}>
                                <span className={styles.linePrefix}>
                                  {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
                                </span>
                                <code>{line.content}</code>
                              </td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
