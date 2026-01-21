import { useEffect, useState, useCallback } from 'react';
import styles from './ProjectGallery.module.css';

interface Project {
  id: string;
  title: string;
  description?: string;
  category?: string;
  screenshot_url?: string;
  preview_url?: string;
  like_count: number;
  completed_at: string;
}

interface ProjectGalleryProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ProjectGallery({ isOpen, onClose }: ProjectGalleryProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch projects from API
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/live/projects');
      if (response.ok) {
        const data = await response.json();
        setProjects(data.projects || []);
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen, fetchProjects]);

  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  // Format date
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return '';
      return date.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
    } catch {
      return '';
    }
  };

  // Open project in new tab
  const openProject = (project: Project) => {
    if (project.preview_url) {
      window.open(project.preview_url, '_blank');
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <span className={styles.headerIcon}>🏆</span>
            <h2>Projetos Finalizados</h2>
          </div>
          <button className={styles.closeButton} onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Content */}
        <div className={styles.content}>
          {loading ? (
            <div className={styles.loading}>
              <div className={styles.spinner} />
              <span>Carregando projetos...</span>
            </div>
          ) : projects.length === 0 ? (
            <div className={styles.empty}>
              <span className={styles.emptyIcon}>📭</span>
              <span className={styles.emptyText}>Nenhum projeto finalizado ainda</span>
              <span className={styles.emptyHint}>Os projetos aparecem aqui quando a IA termina de criar!</span>
            </div>
          ) : (
            <div className={styles.grid}>
              {projects.map((project) => (
                <div
                  key={project.id}
                  className={styles.projectCard}
                  onClick={() => openProject(project)}
                >
                  {/* Preview - iframe or screenshot */}
                  <div className={styles.projectPreview}>
                    {project.preview_url ? (
                      <iframe
                        src={project.preview_url}
                        className={styles.projectIframe}
                        title={project.title}
                        loading="lazy"
                        sandbox="allow-scripts allow-same-origin"
                      />
                    ) : (
                      <div className={styles.projectPlaceholder}>
                        <span className={styles.placeholderEmoji}>📦</span>
                      </div>
                    )}
                    <div className={styles.projectOverlay}>
                      <span className={styles.viewText}>🚀 Abrir Projeto</span>
                    </div>
                  </div>

                  {/* Info */}
                  <div className={styles.projectInfo}>
                    <h3 className={styles.projectTitle}>{project.title}</h3>
                    <div className={styles.projectMeta}>
                      <span className={styles.projectDate}>{formatDate(project.completed_at)}</span>
                      {project.like_count > 0 && (
                        <span className={styles.projectLikes}>❤️ {project.like_count}</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <span className={styles.footerText}>
            {projects.length} {projects.length === 1 ? 'projeto criado' : 'projetos criados'} pela IA
          </span>
        </div>
      </div>
    </div>
  );
}
