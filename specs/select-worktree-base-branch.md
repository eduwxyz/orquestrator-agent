# Seleção de Branch Base para Worktree no Modal de Criação

## 1. Resumo

Adicionar campo de seleção de branch base no modal de criação de cards, permitindo que o usuário escolha de qual branch o worktree será originado. Se não selecionada, usará 'main' como padrão.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar dropdown para seleção de branch base no modal de criação
- [x] Criar endpoint para listar branches disponíveis no repositório
- [x] Modificar criação de worktree para usar a branch selecionada
- [x] Manter 'main' como branch padrão quando não selecionada

### Fora do Escopo
- Permitir criar nova branch diretamente do modal
- Validação de permissões de branch
- Sincronização com branches remotas

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/main.py` | Criar | Endpoint GET /api/git/branches para listar branches |
| `backend/src/git_workspace.py` | Criar | Método para listar todas as branches do repositório |
| `backend/src/schemas/card.py` | Modificar | Adicionar campo opcional base_branch ao CardCreate |
| `backend/src/main.py` | Modificar | Aceitar base_branch na criação de card |
| `frontend/src/api/git.ts` | Criar | Cliente API para endpoints do git |
| `frontend/src/components/AddCardModal/AddCardModal.tsx` | Modificar | Adicionar campo de seleção de branch |
| `frontend/src/api/cards.ts` | Modificar | Incluir base_branch na criação de card |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipo para branch base |

### Detalhes Técnicos

#### Backend - Novo endpoint para listar branches

```python
# backend/src/main.py
@app.get("/api/git/branches")
async def list_git_branches(db: AsyncSession = Depends(get_db)):
    """Lista todas as branches do repositório git."""

    project = await get_active_project(db)
    if not project:
        return {"success": True, "branches": []}

    # Verificar se é repositório git
    git_dir = Path(project.path) / ".git"
    if not git_dir.exists():
        return {"success": True, "branches": []}

    git_manager = GitWorkspaceManager(project.path)
    branches = await git_manager.list_all_branches()

    return {
        "success": True,
        "branches": branches,
        "defaultBranch": await git_manager._get_default_branch()
    }
```

#### Backend - Método para listar branches

```python
# backend/src/git_workspace.py
async def list_all_branches(self) -> List[Dict[str, any]]:
    """Lista todas as branches locais e remotas do repositório."""

    # Listar branches locais
    returncode, stdout, _ = await self._run_git_command(
        ["git", "branch", "--format=%(refname:short)"]
    )

    local_branches = []
    if returncode == 0:
        for branch in stdout.strip().split('\n'):
            if branch and not branch.startswith('agent/'):
                local_branches.append({
                    "name": branch,
                    "type": "local"
                })

    # Listar branches remotas principais (ignorar agent/*)
    returncode, stdout, _ = await self._run_git_command(
        ["git", "branch", "-r", "--format=%(refname:short)"]
    )

    remote_branches = []
    if returncode == 0:
        for branch in stdout.strip().split('\n'):
            if branch and not branch.startswith('origin/agent/'):
                # Remover prefixo origin/
                clean_name = branch.replace('origin/', '')
                if clean_name not in ['HEAD', 'main', 'master'] and \
                   not any(b['name'] == clean_name for b in local_branches):
                    remote_branches.append({
                        "name": clean_name,
                        "type": "remote"
                    })

    return local_branches + remote_branches
```

#### Backend - Aceitar base_branch na criação

```python
# backend/src/schemas/card.py
class CardCreate(CardBase):
    base_branch: Optional[str] = None  # Branch base para o worktree

# backend/src/main.py - modificar endpoint create_card
@app.post("/api/cards", response_model=CardRead)
async def create_card(card: CardCreate, db: AsyncSession = Depends(get_db)):
    # ... código existente ...

    # Se foi especificada uma base_branch, armazenar temporariamente
    # para usar quando o worktree for criado
    if card.base_branch:
        # Armazenar em metadata ou criar campo no modelo
        new_card.base_branch = card.base_branch
```

#### Backend - Usar base_branch na criação do worktree

```python
# backend/src/main.py - modificar create_card_workspace
@app.post("/api/cards/{card_id}/workspace")
async def create_card_workspace(
    card_id: str,
    request_body: Optional[Dict] = None,
    db: AsyncSession = Depends(get_db)
):
    # ... código existente ...

    # Pegar base_branch do request ou do card
    base_branch = None
    if request_body and "baseBranch" in request_body:
        base_branch = request_body["baseBranch"]

    # Criar worktree com a branch especificada
    result = await git_manager.create_worktree(card_id, base_branch)
```

#### Frontend - Cliente API para Git

```typescript
// frontend/src/api/git.ts
import { API_BASE_URL } from './config';

export interface GitBranch {
  name: string;
  type: 'local' | 'remote';
}

export interface BranchesResponse {
  success: boolean;
  branches: GitBranch[];
  defaultBranch: string;
}

export async function fetchGitBranches(): Promise<BranchesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/git/branches`);

  if (!response.ok) {
    throw new Error(`Failed to fetch branches: ${response.statusText}`);
  }

  return response.json();
}
```

#### Frontend - Adicionar seleção de branch no modal

```typescript
// frontend/src/components/AddCardModal/AddCardModal.tsx

// Adicionar imports
import { fetchGitBranches, type GitBranch } from '../../api/git';

// Adicionar estados
const [baseBranch, setBaseBranch] = useState<string>('');
const [availableBranches, setAvailableBranches] = useState<GitBranch[]>([]);
const [defaultBranch, setDefaultBranch] = useState<string>('main');
const [loadingBranches, setLoadingBranches] = useState(false);

// Carregar branches quando modal abre
useEffect(() => {
  if (isOpen) {
    loadBranches();
  }
}, [isOpen]);

const loadBranches = async () => {
  setLoadingBranches(true);
  try {
    const response = await fetchGitBranches();
    setAvailableBranches(response.branches);
    setDefaultBranch(response.defaultBranch);
    setBaseBranch(response.defaultBranch);
  } catch (error) {
    console.error('Failed to load branches:', error);
    // Silently fail - campo será ocultado se não houver branches
  } finally {
    setLoadingBranches(false);
  }
};

// Adicionar campo no formulário (após description)
{availableBranches.length > 0 && (
  <div className={styles.formSection}>
    <div className={styles.inputGroup}>
      <label className={styles.inputLabel}>
        <span className={styles.labelText}>Base Branch</span>
        <span className={styles.labelOptional}>Optional</span>
      </label>
      <div className={styles.selectWrapper}>
        <select
          className={styles.branchSelect}
          value={baseBranch}
          onChange={(e) => setBaseBranch(e.target.value)}
          disabled={isSubmitting || loadingBranches}
        >
          <option value="">Default ({defaultBranch})</option>
          {availableBranches.map((branch) => (
            <option key={branch.name} value={branch.name}>
              {branch.name} {branch.type === 'remote' ? '(remote)' : ''}
            </option>
          ))}
        </select>
        <div className={styles.selectIcon}>
          <svg width="12" height="7" viewBox="0 0 12 7" fill="none">
            <path d="M1 1L6 6L11 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>
      </div>
      <p className={styles.inputHint}>
        Select the branch from which the worktree will be created
      </p>
      <div className={styles.inputGlow} />
    </div>
  </div>
)}

// Modificar onSubmit para incluir baseBranch
const handleSubmit = async (e: React.FormEvent) => {
  // ... código existente ...
  await onSubmit({
    title: title.trim(),
    description: description.trim(),
    modelPlan,
    modelImplement,
    modelTest,
    modelReview,
    images: previewImages.filter(p => p.file !== null).map(p => p.file as File),
    baseBranch: baseBranch || undefined
  });
};
```

#### Frontend - Estilos para o campo de seleção

```css
/* frontend/src/components/AddCardModal/AddCardModal.module.css */

.selectWrapper {
  position: relative;
  width: 100%;
}

.branchSelect {
  width: 100%;
  padding: 12px 40px 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: inherit;
  appearance: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.branchSelect:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.2);
}

.branchSelect:focus {
  outline: none;
  border-color: var(--accent-purple);
  box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.1);
}

.branchSelect:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.branchSelect option {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.selectIcon {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: rgba(255, 255, 255, 0.5);
}

.inputHint {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}
```

#### Frontend - Modificar criação de card

```typescript
// frontend/src/api/cards.ts
export async function createCard(
  title: string,
  description: string,
  modelPlan: ModelType,
  modelImplement: ModelType,
  modelTest: ModelType,
  modelReview: ModelType,
  baseBranch?: string
): Promise<Card> {
  const response = await fetch(API_ENDPOINTS.cards, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title,
      description: description || null,
      modelPlan,
      modelImplement,
      modelTest,
      modelReview,
      base_branch: baseBranch
    }),
  });
  // ... resto do código ...
}
```

---

## 4. Testes

### Unitários
- [x] Teste do endpoint GET /api/git/branches
- [x] Teste do método list_all_branches no GitWorkspaceManager
- [x] Teste de criação de worktree com branch específica

### Integração
- [x] Campo de seleção aparece apenas quando há branches disponíveis
- [x] Branch padrão é selecionada automaticamente
- [x] Worktree é criado a partir da branch selecionada
- [x] Fallback para 'main' quando nenhuma branch é selecionada

---

## 5. Considerações

- **Segurança:** Filtrar branches do tipo 'agent/*' para não poluir a lista
- **Performance:** Cache da lista de branches por alguns segundos
- **UX:** Mostrar indicador visual para branches remotas vs locais
- **Fallback:** Se o repositório não for git, o campo não aparece