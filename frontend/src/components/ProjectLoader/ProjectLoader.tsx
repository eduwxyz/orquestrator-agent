import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Project } from '../../types';
import { loadProject } from '../../api/projects';
import styles from './ProjectLoader.module.css';
import { FolderOpen, X, Check, AlertCircle } from 'lucide-react';

interface ProjectLoaderProps {
  currentProject: Project | null;
  onProjectLoad: (project: Project) => void;
}

export function ProjectLoader({ currentProject, onProjectLoad }: ProjectLoaderProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projectPath, setProjectPath] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleLoadProject = async () => {
    if (!projectPath.trim()) {
      setError('Por favor, insira o caminho do projeto');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await loadProject(projectPath);
      // Se chegou aqui, o projeto foi carregado com sucesso
      const project: Project = {
        id: Date.now().toString(),
        name: projectPath.split('/').pop() || 'projeto',
        path: projectPath,
        hasClaudeConfig: false,
        loadedAt: new Date().toISOString(),
      };
      onProjectLoad(project);
      setIsModalOpen(false);
      setProjectPath('');
    } catch (err) {
      console.error('Erro ao carregar projeto:', err);

      // Mensagens de erro mais específicas
      if (err instanceof Error) {
        if (err.message.includes('Backend não está rodando')) {
          setError(
            'Servidor não está rodando. ' +
            'Por favor, execute "make backend" em outro terminal.'
          );
        } else if (err.message.includes('não foi possível conectar')) {
          setError(
            'Não foi possível conectar ao servidor. ' +
            'Verifique se o backend está rodando na porta 3001.'
          );
        } else {
          setError(err.message);
        }
      } else {
        setError('Erro desconhecido ao carregar projeto');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setProjectPath('');
    setError(null);
  };

  // Focus trap quando modal abre
  useEffect(() => {
    if (isModalOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isModalOpen]);

  // Escape key handler
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isModalOpen) {
        handleCloseModal();
      }
    };

    if (isModalOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isModalOpen]);

  // Modal content para renderizar via Portal
  const modalContent = isModalOpen && (
    <div className={styles.modalOverlay} onClick={handleCloseModal}>
      <div
        ref={modalRef}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby="modal-description"
      >
        <div className={styles.modalHeader}>
          <h2 id="modal-title">Carregar Projeto</h2>
          <button
            className={styles.closeButton}
            onClick={handleCloseModal}
            aria-label="Fechar modal"
            title="Fechar (ESC)"
          >
            <X size={20} />
          </button>
        </div>

        <div className={styles.modalContent} id="modal-description">
          {currentProject && (
            <div className={styles.currentInfo}>
              <strong>Projeto atual:</strong> {currentProject.name}
              <br />
              <small className={styles.projectPath}>{currentProject.path}</small>
              {currentProject.hasClaudeConfig && (
                <span className={styles.claudeIndicator}>
                  <Check size={14} /> .claude config
                </span>
              )}
            </div>
          )}

          <div className={styles.inputGroup}>
            <label htmlFor="projectPath">Caminho do Projeto:</label>
            <input
              ref={inputRef}
              id="projectPath"
              type="text"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              placeholder="/caminho/para/seu/projeto"
              className={styles.pathInput}
              disabled={isLoading}
              autoComplete="off"
              spellCheck={false}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isLoading) {
                  handleLoadProject();
                }
              }}
            />
            <small className={styles.hint}>
              Insira o caminho completo da pasta do projeto
            </small>
          </div>

          {error && (
            <div className={styles.error} role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className={styles.modalFooter}>
          <button
            className={styles.cancelButton}
            onClick={handleCloseModal}
            disabled={isLoading}
          >
            Cancelar
          </button>
          <button
            className={styles.confirmButton}
            onClick={handleLoadProject}
            disabled={isLoading || !projectPath.trim()}
          >
            {isLoading ? (
              <>
                <span className={styles.loadingSpinner}></span>
                Carregando...
              </>
            ) : (
              'Carregar Projeto'
            )}
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <button
        className={styles.loadButton}
        onClick={() => setIsModalOpen(true)}
        title="Carregar projeto externo"
        aria-label="Abrir modal de carregamento de projeto"
      >
        <FolderOpen size={20} />
        <span>
          Load Project
          {currentProject && (
            <span className={styles.currentProject}>
              ({currentProject.name})
            </span>
          )}
        </span>
      </button>

      {/* Renderizar modal via Portal para garantir z-index correto */}
      {modalContent && createPortal(
        modalContent,
        document.getElementById('modal-root') || document.body
      )}
    </>
  );
}