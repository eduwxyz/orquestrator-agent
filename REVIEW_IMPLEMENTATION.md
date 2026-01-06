# Revisão: Seleção de Branch Base para Worktree no Modal de Criação

**Data da Revisão:** 2024
**Spec Revisada:** `specs/select-worktree-base-branch.md`

---

## Resumo Executivo

| Aspecto | Status | Observação |
|---------|--------|------------|
| Arquivos | 5/8 implementados | 3 componentes críticos do backend faltando |
| Objetivos | 2/4 atendidos | Apenas frontend visual foi implementado |
| Aderência à Spec | **BAIXA** | Implementação crítica no backend não realizada |
| Qualidade Geral | **RUIM** | Build quebrado, testes faltam, integração incompleta |
| **Veredito** | **REPROVADO** | Implementação significativamente incompleta |

---

## Análise Detalhada

### Arquivos Implementados vs. Especificado

#### ✅ Implementados Corretamente

1. **`frontend/src/api/git.ts`** - CRIADO ✓
   - Interfaces `GitBranch` e `BranchesResponse` bem definidas
   - Função `fetchGitBranches()` implementada corretamente
   - Usa corretamente `API_CONFIG.BASE_URL`
   - **Qualidade:** Excelente

2. **`frontend/src/api/cards.ts`** - PARCIALMENTE MODIFICADO ✓
   - Função `createCard()` aceita parâmetro `baseBranch` (linha 91)
   - Passa `baseBranch` no JSON enviado ao backend (linha 105)
   - Mapeamento correto no `mapCardResponseToCard()` (mantém compatibilidade)
   - **Observação:** Campo não é `base_branch` mas `baseBranch` - mismatch com backend

3. **`frontend/src/components/AddCardModal/AddCardModal.tsx`** - PARCIALMENTE MODIFICADO ✓
   - Estados adicionados: `baseBranch`, `availableBranches`, `defaultBranch`, `loadingBranches` (linhas 111-114)
   - `useEffect` para carregar branches quando modal abre (linhas 152-157)
   - Função `loadBranches()` implementada corretamente (linhas 159-172)
   - Campo de seleção renderizado condicionalmente (linhas 495-510)
   - `handleSubmit` inclui `baseBranch` no payload (linha 333)
   - **Qualidade:** Boa, mas falta testes

4. **`frontend/src/components/AddCardModal/AddCardModal.module.css`** - CRIADO ✓
   - Estilos para `.selectWrapper`, `.branchSelect`, `.selectIcon`, `.inputHint` adicionados
   - Estilização consistente com resto do modal
   - Suporta estados `:hover`, `:focus`, `:disabled`
   - **Qualidade:** Boa

#### ❌ NÃO Implementados (Crítico)

1. **`backend/src/main.py`** - Endpoint `/api/git/branches` FALTANDO ✗
   - Especificação (linhas 43-66): Detalhes do endpoint
   - **Impacto CRÍTICO:** Frontend não consegue buscar lista de branches
   - **Localização esperada:** Após linha 437 (comentário sobre Git Worktree Isolation)
   - **Referência válida no código:** Linha 492-525 existe `list_active_branches()`, mas NÃO é `/api/git/branches`

   **Endpoint Esperado:**
   ```python
   @app.get("/api/git/branches")
   async def list_git_branches(db: AsyncSession = Depends(get_db)):
       """Lista todas as branches do repositório git."""
       project = await get_active_project(db)
       if not project:
           return {"success": True, "branches": []}

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

2. **`backend/src/git_workspace.py`** - Método `list_all_branches()` FALTANDO ✗
   - Especificação (linhas 72-108): Implementação detalhada do método
   - **Impacto CRÍTICO:** Não há como listar branches disponíveis
   - **Status encontrado:** Referências ao método em `create_worktree()` mas método não existe
   - **Problema:** Sem este método, o endpoint `/api/git/branches` não funcionará

   **Método Esperado:**
   ```python
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
                   clean_name = branch.replace('origin/', '')
                   if clean_name not in ['HEAD', 'main', 'master'] and \
                      not any(b['name'] == clean_name for b in local_branches):
                       remote_branches.append({
                           "name": clean_name,
                           "type": "remote"
                       })

       return local_branches + remote_branches
   ```

3. **`backend/src/schemas/card.py`** - Campo `base_branch` NÃO adicionado a `CardCreate` ✗
   - Especificação (linhas 113-115): Campo deve estar em `CardCreate`
   - **Impacto CRÍTICO:** Backend rejeita requests com `baseBranch`
   - **Localização esperada:** Linha 54-62 (classe `CardCreate`)
   - **Status atual:** Campo não existe

   **Campo esperado:**
   ```python
   class CardCreate(CardBase):
       parent_card_id: Optional[str] = Field(None, alias="parentCardId")
       is_fix_card: bool = Field(False, alias="isFixCard")
       test_error_context: Optional[str] = Field(None, alias="testErrorContext")
       base_branch: Optional[str] = None  # FALTA ESTE CAMPO
   ```

#### ⚠️ Parcialmente Implementados / Com Divergências

1. **`frontend/src/types/index.ts`** - Tipos
   - `Card` interface NÃO foi modificada conforme esperado
   - Faltam tipos para resposta do endpoint de branches
   - Não há interface `CardDraft` que é usada em `AddCardModal`

2. **`backend/src/main.py`** - `create_card_workspace()` Incompleto
   - Linha 451-489: Função NÃO aceita `base_branch` do request
   - Especificação (linhas 130-148): Deve extrair `baseBranch` do request
   - Chama `create_worktree()` SEM parâmetro `base_branch` (linha 471)
   - **Impacto:** Mesmo que endpoint funcione, worktree não usa branch selecionada

---

## Verificação de Objetivos

### Objetivo 1: Adicionar dropdown para seleção de branch base
- **Status:** ✅ COMPLETO
- **Detalhes:** Dropdown implementado em `AddCardModal.tsx` com estilização CSS
- **Observações:** Funciona apenas visualmente, sem integração backend

### Objetivo 2: Criar endpoint para listar branches
- **Status:** ❌ NÃO IMPLEMENTADO
- **Detalhes:** Endpoint `/api/git/branches` faltando
- **Impacto:** Funcionalidade completamente não funcional
- **Recomendação:** Implementar com prioridade máxima

### Objetivo 3: Modificar criação de worktree para usar branch selecionada
- **Status:** ⚠️ PARCIALMENTE IMPLEMENTADO
- **Detalhes:**
  - `create_worktree()` em `git_workspace.py` aceita parâmetro (linha 112)
  - Mas `create_card_workspace()` em `main.py` não passa o parâmetro
- **Impacto:** Mesmo que usuário selecione branch, não será utilizada
- **Recomendação:** Modificar `create_card_workspace()` para extrair e passar `base_branch`

### Objetivo 4: Manter 'main' como branch padrão
- **Status:** ✅ IMPLEMENTADO
- **Detalhes:**
  - `_get_default_branch()` em `git_workspace.py` (linhas 56-80)
  - `create_worktree()` usa como fallback (linhas 137-138)
- **Qualidade:** Boa, com fallback seguro

---

## Problemas Encontrados

### 🔴 Críticos (Bloqueantes para Deploy)

#### 1. Endpoint `/api/git/branches` não implementado
- **Arquivo:** `backend/src/main.py`
- **Problema:** O endpoint definido na spec não existe
- **Localização esperada:** Após linha 437 ou linha 525
- **Consequência:** Frontend não consegue buscar branches, o campo de seleção fica vazio
- **Severidade:** CRÍTICA - Funcionalidade completamente não funcional

#### 2. Método `list_all_branches()` não existe em `GitWorkspaceManager`
- **Arquivo:** `backend/src/git_workspace.py`
- **Problema:** Método especificado (linhas 72-108) não foi implementado
- **Dependência:** Necessário para o endpoint `/api/git/branches`
- **Severidade:** CRÍTICA - Bloqueia implementação do endpoint

#### 3. Campo `base_branch` não adicionado a `CardCreate` schema
- **Arquivo:** `backend/src/schemas/card.py`
- **Problema:** Schema não foi modificado para aceitar `base_branch`
- **Consequência:** Backend rejeita requests com `baseBranch` com erro 422
- **Severidade:** CRÍTICA - Impede comunicação frontend-backend

#### 4. `create_card_workspace()` não aceita `base_branch`
- **Arquivo:** `backend/src/main.py`, linhas 451-489
- **Problema:**
  - Não extrai `base_branch` do request
  - Não passa para `create_worktree()`
- **Código esperado:**
  ```python
  base_branch = None
  if request_body and "baseBranch" in request_body:
      base_branch = request_body["baseBranch"]
  result = await git_manager.create_worktree(card_id, base_branch)
  ```
- **Severidade:** CRÍTICA - Mesmo selecionando branch, não será utilizada

### ⚠️ Importantes (Funcionais)

#### 5. Mismatch de nomenclatura: `baseBranch` vs `base_branch`
- **Frontend:** Usa `baseBranch` (camelCase)
- **Backend:** Especificação usa `base_branch` (snake_case)
- **Impacto:** Confusão na integração, ambiguidade em tipos
- **Recomendação:** Padronizar para `base_branch` em schemas Python

#### 6. Falta integração com Model `Card`
- **Problema:** Model ORM não foi modificado para ter campo `base_branch`
- **Localização:** `backend/src/models/card.py`
- **Impacto:** Campo não será persistido no banco de dados
- **Recomendação:** Adicionar campo `base_branch: Optional[str]` ao modelo

#### 7. Build falha com erros TypeScript
- **Arquivo:** `frontend/`
- **Erro:** Referências a `mergeStatus` em tipos incompatíveis
- **Impacto:** Aplicação não compila
- **Recomendação:** Resolver conflitos de tipos antes de prosseguir

### 📋 Menores (Melhorias Sugeridas)

#### 8. Faltam testes
- **Backend:** Sem testes para endpoint `/api/git/branches` e método `list_all_branches()`
- **Frontend:** Sem testes para componente de seleção de branch
- **Recomendação:** Adicionar testes unitários e integração

#### 9. Faltam validações
- **Validação 1:** Verificar se branch existe antes de criar worktree
- **Validação 2:** Tratar erro se branch especificada for inválida
- **Recomendação:** Adicionar validações conforme detalhes técnicos

#### 10. Documentação incompleta
- Faltam exemplos de uso
- Falta explicação sobre filtros de branches (`agent/*`)
- Recomendação: Adicionar comentários no código

---

## Divergências da Spec

| Item | Especificado | Implementado | Análise |
|------|---|---|---|
| Endpoint `/api/git/branches` | Deve existir | Não existe | ❌ Falta crítica |
| Método `list_all_branches()` | Deve estar em `git_workspace.py` | Não existe | ❌ Falta crítica |
| Campo `base_branch` em schema | Deve estar em `CardCreate` | Não está | ❌ Falta crítica |
| Dropdown no modal | Deve aparecer quando há branches | Aparece | ✅ Correto |
| Estilos CSS | Detalhados na spec | Implementados | ✅ Correto |
| `create_card_workspace()` | Deve aceitar `baseBranch` | Não aceita | ❌ Falta |
| Fallback para 'main' | Deve existir | Existe | ✅ Correto |
| Filtragem `agent/*` | Deve filtrar | Não há teste | ⚠️ Não testado |

---

## Pontos Positivos

### Implementação Frontend
- ✅ Dropdown UI bem estilizado e consistente
- ✅ Estados React bem gerenciados
- ✅ Integração com hooks de draft funcionando
- ✅ Carregamento assíncrono de branches com estado de loading
- ✅ Fallback gracioso para repos sem git

### Estrutura de Código
- ✅ Interfaces TypeScript bem definidas (`GitBranch`, `BranchesResponse`)
- ✅ Função assíncrona `fetchGitBranches()` corretamente implementada
- ✅ Tratamento de erros com try-catch

### Boas Práticas
- ✅ Uso de `useEffect` para side effects
- ✅ Estados carregando (`loadingBranches`)
- ✅ Condição para mostrar campo apenas com branches disponíveis
- ✅ CSS com estilos responsivos

---

## Recomendações

### Correcções Necessárias (Prioridade Alta)

1. **[BLOQUEANTE] Implementar endpoint `/api/git/branches`**
   - Arquivo: `backend/src/main.py`
   - Inserir após linha 525 (após `cleanup_orphan_worktrees`)
   - Use spec linhas 43-66 como referência
   - Testar com curl/Postman

2. **[BLOQUEANTE] Implementar método `list_all_branches()`**
   - Arquivo: `backend/src/git_workspace.py`
   - Adicionar após método `_cleanup_stale_branch()` (linha 104)
   - Use spec linhas 72-108 como referência
   - Testes: local branches, remote branches, filtragem agent/*

3. **[BLOQUEANTE] Adicionar campo `base_branch` a `CardCreate`**
   - Arquivo: `backend/src/schemas/card.py`
   - Linha 54-62: Adicionar `base_branch: Optional[str] = None`
   - Adicionar alias `alias="baseBranch"` para compatibilidade

4. **[BLOQUEANTE] Adicionar campo ao Model `Card`**
   - Arquivo: `backend/src/models/card.py`
   - Adicionar coluna: `base_branch: Optional[str] = None`
   - Executar migração do banco de dados

5. **[BLOQUEANTE] Modificar `create_card_workspace()`**
   - Arquivo: `backend/src/main.py`, linhas 451-489
   - Extrair `baseBranch` do request
   - Passar para `create_worktree(card_id, base_branch)`

6. **[BLOQUEANTE] Resolver erros TypeScript**
   - Investigar/remover referências a `mergeStatus`
   - Executar `npm run build` até sucesso
   - Verificar se conflita com feature anterior

### Testes a Implementar (Prioridade Alta)

1. **Teste do endpoint `/api/git/branches`**
   ```python
   def test_list_git_branches():
       # Mock de repositório git
       # Verificar resposta com lista de branches
       # Testar fallback para repo não-git
   ```

2. **Teste do método `list_all_branches()`**
   ```python
   async def test_list_all_branches():
       # Mock de comandos git
       # Verificar filtragem de branches agent/*
       # Testar branches locais e remotas
   ```

3. **Teste de integração E2E**
   ```python
   async def test_create_card_with_base_branch():
       # Criar card com base_branch específica
       # Verificar se worktree é criado na branch correta
       # Verificar se card tem branch_name correto
   ```

### Melhorias Sugeridas (Prioridade Média)

1. Adicionar tratamento de erro se branch for inválida
2. Adicionar validação: verificar se branch existe antes de usar
3. Adicionar timeout para busca de branches
4. Adicionar cache de branches para evitar requisições frequentes
5. Adicionar suporte a busca/filtro de branches por nome

### Documentação (Prioridade Baixa)

1. Adicionar comentários explicando filtro `agent/*`
2. Documentar comportamento de fallback para 'main'
3. Adicionar exemplos de uso na spec

---

## Conclusão

### Veredito: **❌ REPROVADO**

A implementação está **criticamente incompleta**. Enquanto o frontend recebeu uma interface visual bem implementada para seleção de branch, os componentes essenciais do backend não foram implementados, tornando a funcionalidade completamente não funcional.

### Análise Crítica

**O que funcionaria:**
- ✅ UI do dropdown funciona e fica bonita
- ✅ Estados React gerenciados corretamente
- ✅ Carregamento assíncrono implementado

**O que NÃO funciona:**
- ❌ Backend não fornece lista de branches (endpoint faltando)
- ❌ Método para listar branches não existe (GitWorkspaceManager)
- ❌ Schema não aceita `base_branch` (CardCreate)
- ❌ Worktree não usa branch selecionada (create_card_workspace não implementado)
- ❌ Build falha por erros TypeScript

### Impacto

Se o usuário tentar usar a funcionalidade:
1. Modal abre, dropdown aparece vazio (nenhuma branch carregada)
2. Seleciona uma branch (não há o quê selecionar)
3. Clica em "Create" → request falha 422 (campo não reconhecido)
4. Mesmo se passasse, worktree seria criado em 'main' (não na branch selecionada)

### Estimativa de Trabalho

- **Backend:** 2-3 horas (3 componentes críticos + 1 integração)
- **Testes:** 1-2 horas (3 testes backend + testes frontend)
- **TypeScript fixes:** 30 minutos - 1 hora
- **Code review:** 30 minutos
- **Total:** 4-7 horas de desenvolvimento + testes

### Próximos Passos Recomendados

1. ✅ Implementar os 3 componentes backend críticos (endpoint + método + schema)
2. ✅ Modificar `create_card_workspace()` para integração
3. ✅ Adicionar campo ao Model `Card`
4. ✅ Resolver erros TypeScript
5. ✅ Implementar testes
6. ✅ Executar validação E2E completa
7. ✅ Re-executar esta revisão para aprovação final

---

## Arquivos Afetados por Esta Revisão

- `backend/src/main.py` - Implementar endpoint + modificar create_card_workspace
- `backend/src/git_workspace.py` - Implementar list_all_branches
- `backend/src/schemas/card.py` - Adicionar base_branch a CardCreate
- `backend/src/models/card.py` - Adicionar base_branch ao modelo
- `backend/tests/` - Adicionar testes
- `frontend/` - Resolver erros TypeScript (mergeStatus)

