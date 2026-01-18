import { useState, useEffect, useCallback } from 'react';
import { CompletedProject } from '../../types/live';
import { API_ENDPOINTS } from '../../api/config';
import styles from './Live.module.css';

interface ProjectGalleryProps {
  sessionId: string;
}

const CATEGORY_ICONS: Record<string, string> = {
  game: '🎮',
  app: '📱',
  site: '🌐',
  tool: '🔧',
};

export function ProjectGallery({ sessionId }: ProjectGalleryProps) {
  const [projects, setProjects] = useState<CompletedProject[]>([]);
  const [likedProjects, setLikedProjects] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);

  // Fetch projects
  useEffect(() => {
    async function fetchProjects() {
      try {
        const response = await fetch(API_ENDPOINTS.live.projects);
        const data = await response.json();
        setProjects(data.projects || []);
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchProjects();
  }, []);

  const handleLike = useCallback(async (projectId: string) => {
    if (likedProjects.has(projectId)) return;

    try {
      const response = await fetch(`${API_ENDPOINTS.live.projects}/${projectId}/like`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });

      const data = await response.json();
      if (data.success) {
        setLikedProjects(prev => new Set([...prev, projectId]));
        setProjects(prev =>
          prev.map(p =>
            p.id === projectId ? { ...p, likeCount: data.new_like_count } : p
          )
        );
      }
    } catch (error) {
      console.error('Failed to like project:', error);
    }
  }, [likedProjects, sessionId]);

  if (isLoading) {
    return (
      <div className={styles.galleryPanel}>
        <h3 className={styles.sectionTitle}>
          <span className={styles.galleryIcon}>🏆</span>
          Completed Projects
        </h3>
        <div className={styles.galleryLoading}>Loading...</div>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className={styles.galleryPanel}>
        <h3 className={styles.sectionTitle}>
          <span className={styles.galleryIcon}>🏆</span>
          Completed Projects
        </h3>
        <div className={styles.galleryEmpty}>
          No completed projects yet. Stay tuned!
        </div>
      </div>
    );
  }

  return (
    <div className={styles.galleryPanel}>
      <h3 className={styles.sectionTitle}>
        <span className={styles.galleryIcon}>🏆</span>
        Completed Projects
      </h3>

      <div className={styles.galleryGrid}>
        {projects.map(project => {
          const isLiked = likedProjects.has(project.id);

          return (
            <div key={project.id} className={styles.projectCard}>
              {project.screenshotUrl ? (
                <img
                  src={project.screenshotUrl}
                  alt={project.title}
                  className={styles.projectImage}
                />
              ) : (
                <div className={styles.projectPlaceholder}>
                  {CATEGORY_ICONS[project.category || ''] || '📦'}
                </div>
              )}

              <div className={styles.projectInfo}>
                <span className={styles.projectTitle}>{project.title}</span>
                {project.category && (
                  <span className={styles.projectCategory}>
                    {CATEGORY_ICONS[project.category]} {project.category}
                  </span>
                )}
              </div>

              <button
                className={`${styles.likeButton} ${isLiked ? styles.liked : ''}`}
                onClick={() => handleLike(project.id)}
                disabled={isLiked}
              >
                <span className={styles.likeIcon}>{isLiked ? '❤️' : '🤍'}</span>
                <span className={styles.likeCount}>{project.likeCount}</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
