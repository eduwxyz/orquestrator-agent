# Plano de Implementação: Sistema Multi-Database por Projeto e Melhorias na UI

## 1. Resumo

Implementar um sistema onde cada projeto carregado tenha seu próprio banco de dados isolado, garantindo separação completa de dados entre projetos. Adicionar funcionalidade de cópia automática da pasta .claude para novos projetos e criar uma interface de gerenciamento rápido de projetos na UI para facilitar a navegação entre projetos recentes.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Criar banco de dados isolado para cada projeto carregado
- [x] Implementar cópia automática da pasta .claude quando projeto não tiver
- [x] Adicionar UI para gerenciamento rápido de projetos (histórico/favoritos)
- [x] Manter compatibilidade com sistema existente

### Fora do Escopo
- Migração de dados entre bancos de projetos
- Sincronização de dados entre projetos
- Sistema de backup automático de bancos

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/database.py` | Modificar | Adicionar sistema de múltiplos bancos por projeto |
| `backend/src/database_manager.py` | Criar | Gerenciador centralizado de bancos de dados |
| `backend/src/project_manager.py` | Modificar | Adicionar cópia de .claude e integração com DB manager |
| `backend/src/models/project_history.py` | Criar | Modelo para histórico de projetos |
| `backend/src/routes/projects.py` | Modificar | Adicionar endpoints para histórico e troca rápida |
| `frontend/src/components/ProjectSwitcher/` | Criar | Componente de troca rápida de projetos |
| `frontend/src/components/ProjectLoader/ProjectLoader.tsx` | Modificar | Integrar com novo sistema |
| `frontend/src/api/projects.ts` | Modificar | Adicionar chamadas para novos endpoints |
| `backend/src/config.py` | Modificar | Adicionar configurações de diretório de bancos |

### Detalhes Técnicos

#### 1. Sistema Multi-Database

**Estrutura de diretórios para bancos:**
```
.project_data/
├── {project_hash_1}/
│   └── database.db
├── {project_hash_2}/
│   └── database.db
└── project_history.db  # Banco global com histórico
```

**backend/src/database_manager.py:**
```python
import os
import hashlib
import shutil
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Dict, Optional

class DatabaseManager:
    def __init__(self, base_data_dir: str = ".project_data"):
        self.base_data_dir = Path(base_data_dir)
        self.base_data_dir.mkdir(exist_ok=True)
        self.engines: Dict[str, Any] = {}
        self.sessions: Dict[str, Any] = {}
        self.current_project_id: Optional[str] = None

    def get_project_id(self, project_path: str) -> str:
        """Generate unique ID for project based on path."""
        return hashlib.md5(project_path.encode()).hexdigest()

    def get_database_path(self, project_id: str) -> Path:
        """Get database path for a project."""
        project_dir = self.base_data_dir / project_id
        project_dir.mkdir(exist_ok=True)
        return project_dir / "database.db"

    async def initialize_project_database(self, project_path: str) -> str:
        """Initialize or get database for a project."""
        project_id = self.get_project_id(project_path)
        db_path = self.get_database_path(project_id)

        if project_id not in self.engines:
            # Create new engine for this project
            database_url = f"sqlite+aiosqlite:///{db_path}"
            engine = create_async_engine(database_url, echo=False)

            # Create session maker
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            self.engines[project_id] = engine
            self.sessions[project_id] = async_session

            # Create tables if new database
            if not db_path.exists():
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

        self.current_project_id = project_id
        return project_id

    def get_current_session(self):
        """Get session for current project."""
        if not self.current_project_id:
            raise RuntimeError("No project loaded")
        return self.sessions[self.current_project_id]

    async def close_all(self):
        """Close all database connections."""
        for engine in self.engines.values():
            await engine.dispose()

# Global instance
db_manager = DatabaseManager()
```

**Modificação em backend/src/database.py:**
```python
from .database_manager import db_manager

# Replace direct session maker with dynamic one
def get_session():
    """Get session for current project."""
    return db_manager.get_current_session()

async def get_db():
    """Dependency for FastAPI routes."""
    async with get_session()() as session:
        yield session
```

#### 2. Cópia Automática da Pasta .claude

**Modificação em backend/src/project_manager.py:**
```python
import shutil
from pathlib import Path

class ProjectManager:
    def __init__(self, root_dir: str = None):
        # ... existing code ...
        self.root_claude_path = Path(self.root_dir) / ".claude"

    async def load_project(self, project_path: str) -> dict:
        """Load a project with automatic .claude setup."""
        path = Path(project_path).resolve()

        if not path.exists() or not path.is_dir():
            raise ValueError(f"Invalid project path: {project_path}")

        # Check for .claude folder
        project_claude = path / ".claude"

        # Copy .claude from root if doesn't exist
        if not project_claude.exists() and self.root_claude_path.exists():
            print(f"[ProjectManager] Copying .claude from root to {project_claude}")
            shutil.copytree(
                self.root_claude_path,
                project_claude,
                ignore=shutil.ignore_patterns('*.pyc', '__pycache__', '.git')
            )
            has_claude_config = True
            claude_config_path = str(project_claude)
        else:
            has_claude_config = project_claude.exists()
            claude_config_path = str(project_claude) if has_claude_config else str(self.root_claude_path)

        # Initialize project database
        from .database_manager import db_manager
        project_id = await db_manager.initialize_project_database(str(path))

        # Save to project history (global database)
        await self._save_to_history(project_id, path, path.name)

        # ... rest of existing code ...

        return {
            "id": project_id,
            "path": str(path),
            "name": path.name,
            "has_claude_config": has_claude_config,
            "claude_config_path": claude_config_path,
            "loaded_at": datetime.utcnow().isoformat(),
        }

    async def _save_to_history(self, project_id: str, path: Path, name: str):
        """Save project to global history database."""
        # Use separate global database for history
        # Implementation details below
        pass
```

#### 3. UI para Gerenciamento Rápido de Projetos

**frontend/src/components/ProjectSwitcher/ProjectSwitcher.tsx:**
```tsx
import React, { useState, useEffect } from 'react';
import { Clock, Star, FolderOpen, ChevronDown, Search } from 'lucide-react';
import { Project } from '../../types';
import { getRecentProjects, loadProject, toggleFavorite } from '../../api/projects';
import './ProjectSwitcher.css';

interface ProjectSwitcherProps {
  currentProject: Project | null;
  onProjectSwitch: (project: Project) => void;
}

export const ProjectSwitcher: React.FC<ProjectSwitcherProps> = ({
  currentProject,
  onProjectSwitch,
}) => {
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
      const loaded = await loadProject(project.path);
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
    <div className="project-switcher">
      <button
        className="project-switcher-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <FolderOpen size={18} />
        <span>{currentProject?.name || 'No project loaded'}</span>
        <ChevronDown size={16} className={isOpen ? 'rotate-180' : ''} />
      </button>

      {isOpen && (
        <div className="project-switcher-dropdown">
          <div className="project-switcher-tabs">
            <button
              className={activeTab === 'recent' ? 'active' : ''}
              onClick={() => setActiveTab('recent')}
            >
              <Clock size={16} />
              Recent
            </button>
            <button
              className={activeTab === 'favorites' ? 'active' : ''}
              onClick={() => setActiveTab('favorites')}
            >
              <Star size={16} />
              Favorites
            </button>
          </div>

          <div className="project-switcher-search">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search projects..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>

          <div className="project-switcher-list">
            {loading ? (
              <div className="loading">Loading projects...</div>
            ) : filteredProjects.length > 0 ? (
              filteredProjects.map(project => (
                <div
                  key={project.id}
                  className={`project-item ${project.id === currentProject?.id ? 'current' : ''}`}
                  onClick={() => handleProjectSelect(project)}
                >
                  <div className="project-info">
                    <div className="project-name">{project.name}</div>
                    <div className="project-path">{project.path}</div>
                    <div className="project-meta">
                      {project.hasClaudeConfig && (
                        <span className="has-claude">.claude</span>
                      )}
                      <span className="last-used">
                        {new Date(project.loadedAt).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <button
                    className={`favorite-btn ${project.isFavorite ? 'active' : ''}`}
                    onClick={(e) => handleToggleFavorite(project, e)}
                  >
                    <Star size={16} fill={project.isFavorite ? 'currentColor' : 'none'} />
                  </button>
                </div>
              ))
            ) : (
              <div className="no-projects">
                No {activeTab} projects found
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
```

**frontend/src/components/ProjectSwitcher/ProjectSwitcher.css:**
```css
.project-switcher {
  position: relative;
}

.project-switcher-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.project-switcher-trigger:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}

.project-switcher-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 400px;
  max-height: 500px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  z-index: 1000;
}

.project-switcher-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}

.project-switcher-tabs button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.project-switcher-tabs button.active {
  color: var(--primary);
  background: var(--bg-secondary);
  position: relative;
}

.project-switcher-tabs button.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary);
}

.project-switcher-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--border-color);
}

.project-switcher-search input {
  flex: 1;
  padding: 6px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  outline: none;
}

.project-switcher-list {
  max-height: 350px;
  overflow-y: auto;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.project-item:hover {
  background: var(--bg-hover);
}

.project-item.current {
  background: var(--bg-selected);
}

.project-info {
  flex: 1;
  min-width: 0;
}

.project-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.project-path {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-tertiary);
}

.has-claude {
  padding: 2px 6px;
  background: var(--success-bg);
  color: var(--success);
  border-radius: 3px;
}

.favorite-btn {
  padding: 6px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-secondary);
  transition: color 0.2s;
}

.favorite-btn:hover,
.favorite-btn.active {
  color: var(--warning);
}

.loading,
.no-projects {
  padding: 24px;
  text-align: center;
  color: var(--text-secondary);
}
```

#### 4. Modelo de Histórico de Projetos

**backend/src/models/project_history.py:**
```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from sqlalchemy.sql import func
from ..database import Base

class ProjectHistory(Base):
    __tablename__ = "project_history"

    id = Column(String, primary_key=True)  # project hash
    path = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    has_claude_config = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    last_accessed = Column(DateTime, server_default=func.now(), onupdate=func.now())
    first_accessed = Column(DateTime, server_default=func.now())
    access_count = Column(Integer, default=1)
    metadata = Column(Text, nullable=True)  # JSON with extra info
```

#### 5. Novos Endpoints da API

**Modificação em backend/src/routes/projects.py:**
```python
@router.get("/api/projects/recent")
async def get_recent_projects(
    limit: int = 10,
    filter_type: str = "recent"  # recent or favorites
):
    """Get recent or favorite projects."""
    # Query from global history database
    async with get_history_db() as session:
        query = select(ProjectHistory)

        if filter_type == "favorites":
            query = query.where(ProjectHistory.is_favorite == True)

        query = query.order_by(ProjectHistory.last_accessed.desc()).limit(limit)
        result = await session.execute(query)
        projects = result.scalars().all()

        return [
            {
                "id": p.id,
                "path": p.path,
                "name": p.name,
                "hasClaudeConfig": p.has_claude_config,
                "isFavorite": p.is_favorite,
                "loadedAt": p.last_accessed.isoformat(),
                "accessCount": p.access_count,
            }
            for p in projects
        ]

@router.post("/api/projects/{project_id}/favorite")
async def toggle_favorite(project_id: str):
    """Toggle favorite status of a project."""
    async with get_history_db() as session:
        project = await session.get(ProjectHistory, project_id)
        if project:
            project.is_favorite = not project.is_favorite
            await session.commit()
            return {"success": True, "isFavorite": project.is_favorite}
        return {"success": False, "error": "Project not found"}

@router.post("/api/projects/quick-switch")
async def quick_switch_project(request: dict):
    """Quick switch to a project from history."""
    project_path = request.get("path")

    # Load project using existing logic
    project = await project_manager.load_project(project_path)

    # Update history
    async with get_history_db() as session:
        history = await session.get(ProjectHistory, project["id"])
        if history:
            history.access_count += 1
            history.last_accessed = func.now()
            await session.commit()

    return {"success": True, "project": project}
```

---

## 4. Testes

### Unitários
- [ ] Teste criação de banco isolado por projeto
- [ ] Teste cópia automática de .claude
- [ ] Teste histórico de projetos
- [ ] Teste troca rápida entre projetos
- [ ] Teste favoritos de projetos

### Integração
- [ ] Teste fluxo completo de carregar projeto → criar DB → copiar .claude
- [ ] Teste persistência de dados entre trocas de projeto
- [ ] Teste UI de gerenciamento de projetos

---

## 5. Considerações

### Riscos
- **Espaço em disco:** Múltiplos bancos podem consumir espaço significativo
  - **Mitigação:** Implementar limpeza automática de bancos antigos não utilizados
- **Performance:** Múltiplas conexões de banco podem impactar performance
  - **Mitigação:** Implementar pool de conexões com limite máximo

### Dependências
- Nenhuma biblioteca adicional necessária
- Sistema usa apenas SQLAlchemy e SQLite já existentes

### Melhorias Futuras
- Sistema de backup automático de bancos
- Exportação/importação de dados entre projetos
- Sincronização seletiva de configurações entre projetos
- Compactação automática de bancos antigos