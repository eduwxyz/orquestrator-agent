## 1. Resumo

Implementar funcionalidade de carregamento de projetos externos no kanban board, permitindo que o usuário trabalhe com múltiplos projetos diferentes, cada um com suas próprias features e configurações, utilizando os comandos e skills da pasta .claude do projeto raiz quando não houver .claude específico.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar botão "Load Project" na interface para carregar projetos de diferentes pastas
- [x] Permitir que o usuário navegue e selecione uma pasta de projeto
- [x] Verificar se o projeto selecionado possui pasta .claude própria
- [x] Carregar comandos e skills do .claude da raiz quando não houver no projeto
- [x] Persistir o projeto carregado atualmente no backend
- [x] Adaptar execução dos comandos para usar o diretório do projeto carregado

### Fora do Escopo
- Múltiplos projetos carregados simultaneamente (apenas um por vez)
- Migração automática de cards entre projetos
- Interface de gerenciamento de múltiplos projetos

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/ProjectLoader/ProjectLoader.tsx` | Criar | Componente para seleção e carregamento de projetos |
| `frontend/src/components/ProjectLoader/ProjectLoader.module.css` | Criar | Estilos do componente ProjectLoader |
| `frontend/src/App.tsx` | Modificar | Adicionar ProjectLoader e estado do projeto atual |
| `frontend/src/api/projects.ts` | Criar | API client para endpoints de projetos |
| `backend/src/routes/projects.py` | Criar | Rotas para gerenciamento de projetos |
| `backend/src/models/project.py` | Criar | Modelo para armazenar projeto ativo |
| `backend/src/project_manager.py` | Criar | Gerenciador de projetos e configurações .claude |
| `backend/src/main.py` | Modificar | Incluir rotas de projetos |
| `backend/src/agent.py` | Modificar | Adaptar execução para usar diretório do projeto |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos para Project |

### Detalhes Técnicos

#### Frontend - Componente ProjectLoader

```typescript
// frontend/src/components/ProjectLoader/ProjectLoader.tsx
interface ProjectLoaderProps {
  currentProject: Project | null;
  onProjectLoad: (project: Project) => void;
}

interface Project {
  id: string;
  path: string;
  name: string;
  hasClaudeConfig: boolean;
  loadedAt: string;
}

export function ProjectLoader({ currentProject, onProjectLoad }: ProjectLoaderProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [projectPath, setProjectPath] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLoadProject = async () => {
    setIsLoading(true);
    try {
      const response = await loadProject(projectPath);
      onProjectLoad(response.project);
      setIsModalOpen(false);
    } catch (error) {
      alert('Erro ao carregar projeto');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <button onClick={() => setIsModalOpen(true)}>
        Load Project {currentProject && `(${currentProject.name})`}
      </button>
      {/* Modal com input para path do projeto */}
    </>
  );
}
```

#### Backend - Gerenciador de Projetos

```python
# backend/src/project_manager.py
import os
from pathlib import Path
from typing import Optional, Dict, Any

class ProjectManager:
    """Gerencia projetos e configurações .claude."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.current_project: Optional[Path] = None

    def load_project(self, project_path: str) -> Dict[str, Any]:
        """Carrega um projeto e verifica configuração .claude."""
        path = Path(project_path)

        if not path.exists() or not path.is_dir():
            raise ValueError(f"Caminho inválido: {project_path}")

        # Verifica se tem .claude no projeto
        has_claude = (path / ".claude").exists()

        # Se não tem, prepara para usar do root
        claude_path = path / ".claude" if has_claude else self.root_path / ".claude"

        self.current_project = path

        return {
            "id": str(hash(project_path)),
            "path": str(path),
            "name": path.name,
            "has_claude_config": has_claude,
            "claude_config_path": str(claude_path),
            "loaded_at": datetime.now().isoformat()
        }

    def get_working_directory(self) -> str:
        """Retorna o diretório de trabalho atual."""
        return str(self.current_project) if self.current_project else str(self.root_path)

    def get_claude_config_path(self) -> Path:
        """Retorna o caminho da configuração .claude a ser usada."""
        if self.current_project:
            project_claude = self.current_project / ".claude"
            if project_claude.exists():
                return project_claude
        return self.root_path / ".claude"
```

#### Backend - Rotas de Projetos

```python
# backend/src/routes/projects.py
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Instância global do gerenciador
project_manager: Optional[ProjectManager] = None

@router.post("/load")
async def load_project(request: LoadProjectRequest):
    """Carrega um novo projeto."""
    global project_manager

    if not project_manager:
        # Inicializa com o diretório pai do backend
        project_manager = ProjectManager(Path(__file__).parent.parent.parent)

    try:
        project_info = project_manager.load_project(request.path)

        # Salvar no banco de dados
        async with async_session_maker() as session:
            # Limpar projetos anteriores
            await session.execute(delete(ActiveProject))

            # Salvar novo projeto ativo
            active_project = ActiveProject(**project_info)
            session.add(active_project)
            await session.commit()

        return LoadProjectResponse(
            success=True,
            project=project_info
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/current")
async def get_current_project():
    """Retorna o projeto atualmente carregado."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc())
        )
        project = result.scalar_one_or_none()

        if project:
            return CurrentProjectResponse(
                success=True,
                project=project.to_dict()
            )
        return CurrentProjectResponse(
            success=True,
            project=None
        )
```

#### Modificação do Agent para usar projeto

```python
# backend/src/agent.py - modificações
async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,  # Este será sobrescrito pelo projeto
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    # Obter diretório do projeto atual
    from .routes.projects import project_manager

    if project_manager and project_manager.current_project:
        cwd = project_manager.get_working_directory()

        # Copiar comandos e skills se necessário
        claude_config = project_manager.get_claude_config_path()
        # ... lógica para garantir que comandos estejam disponíveis

    # Resto da implementação continua igual, mas usando cwd do projeto
```

---

## 4. Testes

### Unitários
- [x] Teste de carregamento de projeto válido
- [x] Teste de projeto sem pasta .claude (deve usar root)
- [x] Teste de projeto inválido/inexistente
- [x] Teste de persistência do projeto ativo

### Integração
- [ ] Teste de execução de comando /plan com projeto carregado
- [ ] Teste de uso de comandos do .claude raiz quando projeto não tem
- [ ] Teste de troca entre projetos diferentes

---

## 5. Considerações

- **Riscos:**
  - Possíveis conflitos de path entre diferentes sistemas operacionais
  - Permissões de acesso a diretórios externos
  - Mitigação: Validação robusta de paths e tratamento de erros

- **Dependências:**
  - Frontend precisa de método para selecionar diretórios (pode usar input text inicialmente)
  - Backend precisa manter estado do projeto atual entre requisições

- **Melhorias Futuras:**
  - Adicionar histórico de projetos recentes
  - Permitir configurações específicas por projeto
  - Interface mais rica para seleção de diretórios (file picker nativo)