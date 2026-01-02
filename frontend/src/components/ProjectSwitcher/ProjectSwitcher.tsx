import { useState, useEffect } from 'react';
import { Clock, Star, FolderOpen, ChevronDown, Search } from 'lucide-react';
import { Project } from '../../types';
import { getRecentProjects, quickSwitchProject, toggleFavorite } from '../../api/projects';
import styles from './ProjectSwitcher.module.css';

interface ProjectSwitcherProps {
  currentProject: Project | null;
  onProjectSwitch: (project: Project) => void;
}

export function ProjectSwitcher({ currentProject, onProjectSwitch }: ProjectSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'recent' | 'favorites'>('recent');

  useEffect(() => {
    if (isOpen) {
      loadProjects();
    }
  }, [isOpen, activeTab]);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const projectList = await getRecentProjects(activeTab);
      setProjects(projectList);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSelect = async (project: Project) => {
    try {
      const loaded = await quickSwitchProject(project.path);
      onProjectSwitch(loaded);
      setIsOpen(false);
    } catch (error) {
      console.error('Failed to switch project:', error);
    }
  };

  const handleToggleFavorite = async (project: Project, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await toggleFavorite(project.id);
      await loadProjects();
    } catch (error) {
      console.error('Failed to toggle favorite:', error);
    }
  };

  const filteredProjects = projects.filter(p =>
    p.name.toLowerCase().includes(filter.toLowerCase()) ||
    p.path.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className={styles.projectSwitcher}>
      <button
        className={styles.projectSwitcherTrigger}
        onClick={() => setIsOpen(!isOpen)}
      >
        <FolderOpen size={18} />
        <span>{currentProject?.name || 'No project loaded'}</span>
        <ChevronDown size={16} className={isOpen ? styles.rotate180 : ''} />
      </button>

      {isOpen && (
        <div className={styles.projectSwitcherDropdown}>
          <div className={styles.projectSwitcherTabs}>
            <button
              className={activeTab === 'recent' ? styles.active : ''}
              onClick={() => setActiveTab('recent')}
            >
              <Clock size={16} />
              Recent
            </button>
            <button
              className={activeTab === 'favorites' ? styles.active : ''}
              onClick={() => setActiveTab('favorites')}
            >
              <Star size={16} />
              Favorites
            </button>
          </div>

          <div className={styles.projectSwitcherSearch}>
            <Search size={16} />
            <input
              type="text"
              placeholder="Search projects..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>

          <div className={styles.projectSwitcherList}>
            {loading ? (
              <div className={styles.loading}>Loading projects...</div>
            ) : filteredProjects.length > 0 ? (
              filteredProjects.map(project => (
                <div
                  key={project.id}
                  className={`${styles.projectItem} ${project.id === currentProject?.id ? styles.current : ''}`}
                  onClick={() => handleProjectSelect(project)}
                >
                  <div className={styles.projectInfo}>
                    <div className={styles.projectName}>{project.name}</div>
                    <div className={styles.projectPath}>{project.path}</div>
                    <div className={styles.projectMeta}>
                      {project.hasClaudeConfig && (
                        <span className={styles.hasClaude}>.claude</span>
                      )}
                      <span className={styles.lastUsed}>
                        {new Date(project.loadedAt).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <button
                    className={`${styles.favoriteBtn} ${project.isFavorite ? styles.activeFavorite : ''}`}
                    onClick={(e) => handleToggleFavorite(project, e)}
                  >
                    <Star size={16} fill={project.isFavorite ? 'currentColor' : 'none'} />
                  </button>
                </div>
              ))
            ) : (
              <div className={styles.noProjects}>
                No {activeTab} projects found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
