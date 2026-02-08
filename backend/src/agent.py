import re
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

from .execution import (
    ExecutionLog,
    ExecutionRecord,
    ExecutionStatus,
    LogType,
    PlanResult,
)

from .repositories.execution_repository import ExecutionRepository
from .models.execution import ExecutionStatus as DBExecutionStatus
from .git_workspace import GitWorkspaceManager
from .services.execution_ws import execution_ws_manager

# Store executions in memory (mantido para compatibilidade durante migração)
executions: dict[str, ExecutionRecord] = {}


def _is_retryable(error: str) -> bool:
    """Verifica se erro e transiente e pode ser retentado"""
    retryable = ["connection", "timeout", "rate limit", "overloaded", "503", "502", "529"]
    return any(r in error.lower() for r in retryable)


async def execute_with_retry(
    execute_fn,
    card_id: str,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> PlanResult:
    """Executa funcao com retry automatico em erros transientes"""
    last_error = None

    for attempt in range(max_retries):
        try:
            result = await execute_fn()

            if result.success:
                return result

            # So retry em erros de conexao/timeout
            if result.error and not _is_retryable(result.error):
                return result

            last_error = result.error

        except Exception as e:
            last_error = str(e)
            if not _is_retryable(str(e)):
                raise

        if attempt < max_retries - 1:
            delay = retry_delay * (2 ** attempt)
            print(f"[{card_id[:8]}] Retry {attempt + 1}/{max_retries} em {delay:.1f}s...")
            await asyncio.sleep(delay)

    return PlanResult(
        success=False,
        error=f"Falhou apos {max_retries} tentativas: {last_error}",
        logs=[]
    )

# =============================================================================
# Prompts do Gemini CLI (embutidos para funcionar em worktrees)
# O Gemini CLI não reconhece comandos customizados quando executado em worktrees
# porque .git é um arquivo (não pasta) em worktrees, então embutimos as instruções
# =============================================================================

GEMINI_PLAN_PROMPT = """
# Plan

Crie um plano de implementação detalhado com base na solicitação do usuário: {arguments}

Salve o planejamento em `specs/<nome_descritivo>.md`

## Instruções

1. Se a solicitação estiver vazia, pergunte ao usuário o que deseja implementar
2. Analise toda a codebase para entender padrões existentes
3. Gere um nome descritivo e curto para o arquivo
4. Inclua snippets de código quando fizer sentido
5. Identifique o tipo de tarefa (feature, bug, refactor, etc.)

## Workflow

1. Analise a solicitação e requisitos do usuário
2. Analise a codebase para manter consistência com padrões existentes
3. Documente decisões arquiteturais e motivos das escolhas
4. Salve o arquivo em `specs/`
5. Apresente um resumo ao usuário com o que deve ser feito

## Formato do Plano

## 1. Resumo

Breve descrição do que será implementado (2-3 frases), incluindo o problema/necessidade que motivou.

---

## 2. Objetivos e Escopo

### Objetivos
- [ ] Objetivo 1
- [ ] Objetivo 2

### Fora do Escopo
- Item 1 (se aplicável)

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `path/to/file.ts` | Modificar/Criar | Descrição da mudança |

### Detalhes Técnicos

Descreva a abordagem técnica, incluindo snippets de código quando relevante.

---

## 4. Testes

### Unitários
- [ ] Teste 1
- [ ] Teste 2

### Integração (se aplicável)
- [ ] Teste 1

---

## 5. Considerações (opcional)

- **Riscos:** Possíveis riscos e como mitigar
- **Dependências:** PRs, aprovações ou sistemas externos necessários
"""

GEMINI_IMPLEMENT_PROMPT = """
# Implement

Implemente o plano especificado.

## Conteúdo do Plano

{spec_content}

## Instruções

1. Leia o plano acima cuidadosamente
2. Analise todas as seções do plano
3. Implemente cada item na ordem definida
4. Atualize o arquivo de plano marcando checkboxes conforme conclui cada item

## Workflow de Implementação

### Fase 1: Análise do Plano

1. Extraia a lista de arquivos a serem modificados/criados da tabela
2. Extraia os objetivos e escopo
3. Extraia os detalhes técnicos e snippets de código
4. Crie uma lista de tarefas baseada nos itens do plano

### Fase 2: Implementação

Para cada arquivo listado na seção "Arquivos a Serem Modificados/Criados":

1. Se a ação for "Criar":
   - Crie o arquivo seguindo os detalhes técnicos do plano
   - Use os snippets de código como referência

2. Se a ação for "Modificar":
   - Leia o arquivo existente primeiro
   - Aplique as mudanças descritas no plano
   - Mantenha consistência com o código existente

3. Após implementar cada item:
   - Atualize o checkbox correspondente no arquivo de plano: `- [ ]` → `- [x]`

### Fase 3: Testes

1. Implemente os testes unitários listados na seção "Testes"
2. Execute os testes para validar a implementação
3. Marque os checkboxes de testes conforme passam

### Fase 4: Finalização

1. Revise se todos os objetivos foram atendidos
2. Marque todos os checkboxes restantes
3. Apresente um resumo do que foi implementado

## Regras

- **Sempre** siga a ordem definida no plano
- **Sempre** atualize os checkboxes no arquivo de plano conforme progride
- **Nunca** pule etapas definidas no plano
- **Mantenha** consistência com padrões existentes na codebase
"""

GEMINI_TEST_IMPLEMENTATION_PROMPT = """
# Test Implementation

Valide a implementação do plano especificado.

## Conteúdo do Plano

{spec_content}

## Instruções

1. Leia o plano acima cuidadosamente
2. Execute todas as fases de validação abaixo
3. Gere um relatório final de qualidade

## Fases de Validação

### Fase 1: Verificação de Arquivos

1. Extraia a lista de arquivos da seção "Arquivos a Serem Modificados/Criados" do plano
2. Para cada arquivo listado:
   - **Se ação era "Criar"**: Verifique se o arquivo existe
   - **Se ação era "Modificar"**: Verifique se o arquivo foi modificado
3. Registre status de cada arquivo:
   - ✅ Arquivo criado/modificado conforme esperado
   - ❌ Arquivo ausente ou não modificado
   - ⚠️ Arquivo existe mas conteúdo diverge do esperado

### Fase 2: Verificação de Checkboxes

1. Leia o arquivo de plano novamente
2. Extraia todos os checkboxes (`- [ ]` e `- [x]`)
3. Calcule a taxa de conclusão
4. Liste quais itens ainda estão pendentes (se houver)

### Fase 3: Execução de Testes

1. Identifique a seção "Testes" no plano
2. Execute os testes do projeto:
   - Para Python: `pytest`
   - Para Node: `npm test`
   - Para Go: `go test ./...`
3. Capture resultados:
   - ✅ Testes passando
   - ❌ Testes falhando (inclua mensagem de erro)

### Fase 4: Análise de Qualidade

1. **Lint/Formatação**: Execute linter do projeto se disponível
2. **Type Check**: Execute verificação de tipos se aplicável
3. **Build**: Tente compilar/buildar o projeto

## Formato do Relatório Final

```markdown
# Relatório de Validação

## Resumo Executivo
| Métrica | Status |
|---------|--------|
| Arquivos | X/Y criados/modificados |
| Checkboxes | X/Y concluídos |
| Testes | X passando, Y falhando |
| Build | ✅/❌ |

## Detalhes
[detalhes da validação]

## Conclusão
[Status geral: APROVADO / APROVADO COM RESSALVAS / REPROVADO]
```

## Regras

- **Sempre** execute todos os testes disponíveis
- **Nunca** modifique arquivos durante a validação (apenas leitura)
- **Reporte** todos os problemas encontrados
"""

GEMINI_REVIEW_PROMPT = """
# Review Implementation

Revise a implementação do plano especificado.

## Conteúdo do Plano

{spec_content}

## Propósito

Este comando faz uma revisão crítica comparando o que foi planejado na spec com o que foi implementado. Identifique:

- Itens faltantes ou incompletos
- Divergências entre spec e implementação
- Problemas de arquitetura ou padrão
- Oportunidades de melhoria
- Potenciais bugs ou inconsistências

## Fases de Revisão

### Fase 1: Inventário de Arquivos

1. Extraia a lista de arquivos da spec
2. Para cada arquivo:
   - Verifique se existe
   - Leia o conteúdo completo
   - Compare com o que foi especificado
3. Identifique:
   - Arquivos especificados mas não criados
   - Arquivos criados mas não especificados
   - Arquivos com implementação divergente

### Fase 2: Análise de Aderência à Spec

Para cada arquivo implementado:

1. **Estrutura do Código:**
   - Classes/funções esperadas estão presentes?
   - Assinaturas de métodos conferem?
   - Tipos e validações estão corretos?

2. **Lógica de Negócio:**
   - A implementação segue a lógica descrita na spec?
   - Casos de borda foram tratados?

3. **Padrões e Convenções:**
   - Nomenclatura segue o padrão?
   - Arquitetura está sendo respeitada?

### Fase 3: Verificação de Objetivos

Para cada objetivo da spec:
- ✅ Completo: Totalmente implementado
- ⚠️ Parcial: Implementado com lacunas
- ❌ Ausente: Não implementado

### Fase 4: Revisão de Qualidade

1. **Consistência** do código
2. **Robustez** e tratamento de erros
3. **Legibilidade** e clareza
4. **Decisões Arquiteturais**

## Formato do Relatório

```markdown
# Revisão: [nome-da-spec]

## Resumo Executivo
| Aspecto | Status |
|---------|--------|
| Arquivos | X/Y implementados |
| Objetivos | X/Y atendidos |
| Aderência à Spec | Alta/Média/Baixa |
| Qualidade Geral | Boa/Regular/Ruim |

## Problemas Encontrados
[lista de problemas por severidade]

## Recomendações
[ações específicas]

## Conclusão
**Veredito:** [APROVADO / APROVADO COM RESSALVAS / REPROVADO]
```

## Regras

- **Sempre** leia a spec E os arquivos implementados
- **Sempre** seja crítico mas construtivo
- **Nunca** modifique arquivos durante a revisão
- **Compare** detalhadamente spec vs implementação
- **Sugira** correções específicas
"""


def get_model_provider(model: str) -> str:
    """
    Determine provider from model name.

    Args:
        model: Model name (e.g., "opus-4.5", "gemini-3-pro")

    Returns:
        str: Provider name ("anthropic" or "google")
    """
    if model.startswith("gemini"):
        return "google"
    return "anthropic"


async def get_worktree_cwd(card_id: str, project_path: str, db_session: Optional[AsyncSession] = None) -> tuple[str, Optional[str], Optional[str]]:
    """
    Obtem o cwd baseado em worktree para isolamento do card.

    Returns:
        Tuple com (cwd, branch_name, worktree_path)
        Se nao for repo git ou worktree falhar, retorna (project_path, None, None)
    """
    from .repositories.card_repository import CardRepository
    from .schemas.card import CardUpdate

    # Verificar se eh repo git
    git_dir = Path(project_path) / ".git"
    if not git_dir.exists():
        print(f"[Agent] Project is not a git repo, using project path directly")
        return project_path, None, None

    # Obter card para verificar se ja tem worktree
    card = None
    base_branch = None

    if db_session:
        card_repo = CardRepository(db_session)
        card = await card_repo.get_by_id(card_id)

        if card:
            base_branch = card.base_branch
            if card.worktree_path:
                # Verificar se worktree ainda existe
                if Path(card.worktree_path).exists():
                    print(f"[Agent] Using existing worktree: {card.worktree_path}")
                    return card.worktree_path, card.branch_name, card.worktree_path
                else:
                    print(f"[Agent] Worktree path no longer exists, creating new one")

    # Criar novo worktree
    git_manager = GitWorkspaceManager(project_path)
    await git_manager.recover_state()

    if base_branch:
        print(f"[Agent] Creating worktree with base branch: {base_branch}")

    result = await git_manager.create_worktree(card_id, base_branch=base_branch)

    if result.success:
        print(f"[Agent] Created worktree: {result.worktree_path} on branch {result.branch_name}")

        # Atualizar card no banco
        if db_session:
            card_repo = CardRepository(db_session)
            update_data = CardUpdate(
                branch_name=result.branch_name,
                worktree_path=result.worktree_path,
                merge_status="none"
            )
            await card_repo.update(card_id, update_data)
            await db_session.commit()

        return result.worktree_path, result.branch_name, result.worktree_path
    else:
        print(f"[Agent] Failed to create worktree: {result.error}, using project path")
        return project_path, None, None


async def get_execution(card_id: str, db_session: Optional[AsyncSession] = None) -> Optional[dict]:
    """Get execution record by card ID from database or memory."""
    if db_session:
        # Usar repository se db_session estiver disponível
        repo = ExecutionRepository(db_session)
        return await repo.get_execution_with_logs(card_id)
    else:
        # Fallback para memória
        record = executions.get(card_id)
        if record:
            return {
                "cardId": record.card_id,
                "status": record.status.value,
                "logs": [
                    {"timestamp": log.timestamp, "type": log.type.value if hasattr(log.type, "value") else log.type, "content": log.content}
                    for log in record.logs
                ]
            }
        return None


def get_all_executions() -> list[ExecutionRecord]:
    """Get all execution records."""
    return list(executions.values())


def add_log(record: ExecutionRecord, log_type: LogType, content: str) -> None:
    """Add a log entry to the execution record."""
    log = ExecutionLog(
        timestamp=datetime.now().isoformat(),
        type=log_type,
        content=content,
    )
    record.logs.append(log)

    # Criar prefixo com card_id (primeiros 8 caracteres para brevidade)
    card_id_short = record.card_id[:8] if len(record.card_id) > 8 else record.card_id

    # Se o record tiver título, incluir também (limitado)
    if hasattr(record, 'title') and record.title:
        title_short = record.title[:25] + "..." if len(record.title) > 25 else record.title
        card_prefix = f"[{card_id_short}|{title_short}]"
    else:
        card_prefix = f"[{card_id_short}]"

    print(f"{card_prefix} [Agent] [{log_type.value.upper()}] {content}")


def extract_spec_path(text: str) -> Optional[str]:
    """Extrai o caminho do arquivo de spec do texto de resultado."""
    # Padrões comuns para detectar criação de arquivo de spec
    patterns = [
        r"specs/[\w\-]+\.md",
        r"created.*?(specs/[\w\-]+\.md)",
        r"saved.*?(specs/[\w\-]+\.md)",
        r"File created.*?(specs/[\w\-]+\.md)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Retorna o grupo 1 se existir, senão o match completo
            return match.group(1) if match.lastindex else match.group(0)
    return None


async def execute_plan_gemini(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    model: str,
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute plan using Gemini CLI."""
    from .gemini_agent import GeminiAgent
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    gemini = GeminiAgent(model=model)

    # Usar prompt embutido (Gemini CLI não reconhece comandos em worktrees)
    arguments = f"{title}: {description}"
    prompt = GEMINI_PLAN_PROMPT.format(arguments=arguments)

    # Add working directory context to ensure files are saved in the correct location
    prompt += f"\n\n**IMPORTANTE:** O diretório de trabalho é `{cwd}`. Salve todos os arquivos usando caminhos absolutos baseados neste diretório (ex: `{cwd}/specs/nome.md`)."

    if images:
        prompt += "\n\n[Imagens anexadas ao card estão disponíveis para análise]"

    # Usar repository se disponível
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/plan",
            title=title
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Iniciando execução do plano com Gemini para: {title}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Diretório de trabalho: {cwd}"
        )

    # Initialize execution record (memória)
    record = ExecutionRecord(
        cardId=card_id,
        title=title,
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Iniciando execução do plano com Gemini para: {title}")
    add_log(record, LogType.INFO, f"Diretório de trabalho: {cwd}")

    # Executa comando via Gemini CLI
    full_response = ""
    try:
        async for chunk in gemini.execute_command(
            prompt=prompt,
            cwd=Path(cwd),
            stream=True
        ):
            full_response += chunk
            add_log(record, LogType.TEXT, chunk)
            if repo and execution_db:
                await repo.add_log(
                    execution_id=execution_db.id,
                    log_type="text",
                    content=chunk
                )

        # Extrai spec_path e retorna resultado
        spec_path = extract_spec_path(full_response)

        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = full_response
        add_log(record, LogType.INFO, "Execução do plano concluída com sucesso")
        if spec_path:
            add_log(record, LogType.INFO, f"Caminho da spec: {spec_path}")

        if repo and execution_db:
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                project_id=project_id,
                result=full_response
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    spec_path=spec_path,
                    result=full_response,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=True,
            spec_path=spec_path,
            result=full_response,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Erro de execução: {error_message}")

        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_implement_gemini(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str,
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute /implement usando Gemini CLI."""
    from .gemini_agent import GeminiAgent
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    gemini = GeminiAgent(model=model)

    # Ler o conteúdo do arquivo de spec
    spec_file = Path(cwd) / spec_path
    if spec_file.exists():
        spec_content = spec_file.read_text()
    else:
        spec_content = f"[Arquivo de spec não encontrado: {spec_path}]"

    # Usar prompt embutido (Gemini CLI não reconhece comandos em worktrees)
    prompt = GEMINI_IMPLEMENT_PROMPT.format(spec_content=spec_content)
    if images:
        prompt += "\n\n[Imagens anexadas ao card estão disponíveis para análise]"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem

    # Usar repository se disponível
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/implement",
            title=f"impl:{spec_name}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Iniciando implementação com Gemini para: {spec_path}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Diretório de trabalho: {cwd}"
        )

    # Initialize execution record (memória)
    record = ExecutionRecord(
        cardId=card_id,
        title=f"impl:{spec_name}",
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Iniciando implementação com Gemini para: {spec_path}")
    add_log(record, LogType.INFO, f"Diretório de trabalho: {cwd}")

    # Executa comando via Gemini CLI
    full_response = ""
    try:
        async for chunk in gemini.execute_command(
            prompt=prompt,
            cwd=Path(cwd),
            stream=True
        ):
            full_response += chunk
            add_log(record, LogType.TEXT, chunk)
            if repo and execution_db:
                await repo.add_log(
                    execution_id=execution_db.id,
                    log_type="text",
                    content=chunk
                )

        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = full_response
        add_log(record, LogType.INFO, "Implementação concluída com sucesso")

        if repo and execution_db:
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                project_id=project_id,
                result=full_response
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    result=full_response,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=True,
            result=full_response,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Erro de execução: {error_message}")

        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_test_implementation_gemini(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str,
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute /test-implementation usando Gemini CLI."""
    from .gemini_agent import GeminiAgent
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    gemini = GeminiAgent(model=model)

    # Ler o conteúdo do arquivo de spec
    spec_file = Path(cwd) / spec_path
    if spec_file.exists():
        spec_content = spec_file.read_text()
    else:
        spec_content = f"[Arquivo de spec não encontrado: {spec_path}]"

    # Usar prompt embutido (Gemini CLI não reconhece comandos em worktrees)
    prompt = GEMINI_TEST_IMPLEMENTATION_PROMPT.format(spec_content=spec_content)
    if images:
        prompt += "\n\n[Imagens anexadas ao card estão disponíveis para análise]"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem

    # Usar repository se disponível
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/test-implementation",
            title=f"test:{spec_name}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Iniciando teste da implementação com Gemini para: {spec_path}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Diretório de trabalho: {cwd}"
        )

    # Initialize execution record (memória)
    record = ExecutionRecord(
        cardId=card_id,
        title=f"test:{spec_name}",
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Iniciando teste da implementação com Gemini para: {spec_path}")
    add_log(record, LogType.INFO, f"Diretório de trabalho: {cwd}")

    # Executa comando via Gemini CLI
    full_response = ""
    try:
        async for chunk in gemini.execute_command(
            prompt=prompt,
            cwd=Path(cwd),
            stream=True
        ):
            full_response += chunk
            add_log(record, LogType.TEXT, chunk)
            if repo and execution_db:
                await repo.add_log(
                    execution_id=execution_db.id,
                    log_type="text",
                    content=chunk
                )

        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = full_response
        add_log(record, LogType.INFO, "Teste da implementação concluído com sucesso")

        if repo and execution_db:
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                project_id=project_id,
                result=full_response
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    result=full_response,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=True,
            result=full_response,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Erro de execução: {error_message}")

        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_review_gemini(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str,
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute /review usando Gemini CLI."""
    from .gemini_agent import GeminiAgent
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    gemini = GeminiAgent(model=model)

    # Ler o conteúdo do arquivo de spec
    spec_file = Path(cwd) / spec_path
    if spec_file.exists():
        spec_content = spec_file.read_text()
    else:
        spec_content = f"[Arquivo de spec não encontrado: {spec_path}]"

    # Usar prompt embutido (Gemini CLI não reconhece comandos em worktrees)
    prompt = GEMINI_REVIEW_PROMPT.format(spec_content=spec_content)
    if images:
        prompt += "\n\n[Imagens anexadas ao card estão disponíveis para análise]"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem

    # Usar repository se disponível
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/review",
            title=f"review:{spec_name}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Iniciando revisão com Gemini para: {spec_path}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Diretório de trabalho: {cwd}"
        )

    # Initialize execution record (memória)
    record = ExecutionRecord(
        cardId=card_id,
        title=f"review:{spec_name}",
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Iniciando revisão com Gemini para: {spec_path}")
    add_log(record, LogType.INFO, f"Diretório de trabalho: {cwd}")

    # Executa comando via Gemini CLI
    full_response = ""
    try:
        async for chunk in gemini.execute_command(
            prompt=prompt,
            cwd=Path(cwd),
            stream=True
        ):
            full_response += chunk
            add_log(record, LogType.TEXT, chunk)
            if repo and execution_db:
                await repo.add_log(
                    execution_id=execution_db.id,
                    log_type="text",
                    content=chunk
                )

        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = full_response
        add_log(record, LogType.INFO, "Revisão concluída com sucesso")

        if repo and execution_db:
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                project_id=project_id,
                result=full_response
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    result=full_response,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=True,
            result=full_response,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Erro de execução: {error_message}")

        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
    experts: Optional[dict] = None,
) -> PlanResult:
    """Execute a plan using Claude Agent SDK or Gemini CLI."""
    # Detecta se é modelo Gemini
    if model.startswith("gemini"):
        return await execute_plan_gemini(
            card_id, title, description, cwd, model, images, db_session
        )

    # Obter diretório do projeto atual do banco de dados
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            # Fallback: usar o diretório raiz do orquestrator-agent
            # (3 níveis acima: agent.py -> src -> backend -> orquestrator-agent)
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    # Detect provider
    provider = get_model_provider(model)

    # Mapear nome de modelo para valor do SDK (Claude)
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/plan {title}: {description}"

    # Add working directory context to ensure files are saved in the correct location
    prompt += f"\n\n**IMPORTANTE:** O diretório de trabalho é `{cwd}`. Salve todos os arquivos usando caminhos absolutos baseados neste diretório (ex: `{cwd}/specs/nome.md`)."

    # Add expert context if available
    if experts:
        from .services.expert_triage_service import build_expert_context_for_plan
        expert_context = build_expert_context_for_plan(experts, cwd)
        if expert_context:
            prompt += f"\n\n{expert_context}"
            print(f"[Agent] Injected expert context from {len(experts)} experts")

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Usar repository se disponível, senão usar memória
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        # Criar execução no banco
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/plan",
            title=title
        )
        # Log inicial no banco
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Starting plan execution for: {title}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Working directory: {cwd}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Prompt: {prompt}"
        )

    # Initialize execution record (memória - para compatibilidade)
    record = ExecutionRecord(
        cardId=card_id,
        title=title,
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting plan execution for: {title}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""
    spec_path: Optional[str] = None

    try:
        # Configure agent options
        cwd_path = Path(cwd)
        print(f"[Agent] Final CWD being used: {cwd_path.absolute()}")

        if provider == "google":
            # Use Gemini implementation
            from .services.gemini_service import get_gemini_service

            gemini_service = get_gemini_service()

            # Execute using Gemini
            async for chunk in gemini_service.execute_command(
                command="/plan",
                content=f"{title}: {description}",
                model_name=model,
                cwd=str(cwd_path),
                images=images
            ):
                if chunk["type"] == "text":
                    content = chunk["content"]
                    add_log(record, LogType.TEXT, content)
                    # Salva log no banco se disponível
                    if repo and execution_db:
                        await repo.add_log(
                            execution_id=execution_db.id,
                            log_type="text",
                            content=content
                        )
                    result_text += content + "\n"
                    # Tentar extrair spec_path do texto
                    if not spec_path:
                        spec_path = extract_spec_path(content)
                elif chunk["type"] == "error":
                    error_msg = chunk["content"]
                    add_log(record, LogType.ERROR, error_msg)
                    if repo and execution_db:
                        await repo.add_log(
                            execution_id=execution_db.id,
                            log_type="error",
                            content=error_msg
                        )
                    raise RuntimeError(error_msg)

        else:
            # Use Claude Agent SDK
            options = ClaudeAgentOptions(
                cwd=cwd_path,
                setting_sources=["user", "project"],  # Load Skills from .claude/skills/
                allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
                permission_mode="acceptEdits",
                model=sdk_model,
            )

            # Execute using claude-agent-sdk
            try:
                async for message in query(prompt=prompt, options=options):
                    if isinstance(message, AssistantMessage):
                        # Handle assistant messages with content blocks
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                add_log(record, LogType.TEXT, block.text)
                                # Salva log no banco se disponível
                                if repo and execution_db:
                                    await repo.add_log(
                                        execution_id=execution_db.id,
                                        log_type="text",
                                        content=block.text
                                    )
                                result_text += block.text + "\n"
                                # Tentar extrair spec_path do texto
                                if not spec_path:
                                    spec_path = extract_spec_path(block.text)
                            elif isinstance(block, ToolUseBlock):
                                add_log(record, LogType.TOOL, f"Using tool: {block.name}")
                                # Salva log no banco se disponível
                                if repo and execution_db:
                                    await repo.add_log(
                                        execution_id=execution_db.id,
                                        log_type="tool",
                                        content=f"Using tool: {block.name}"
                                    )
                                # Se for Write tool, captura o file_path
                                if block.name == "Write" and hasattr(block, "input"):
                                    tool_input = block.input
                                    if isinstance(tool_input, dict) and "file_path" in tool_input:
                                        file_path = tool_input["file_path"]
                                        if "specs/" in file_path and file_path.endswith(".md"):
                                            spec_path = file_path
                                            add_log(record, LogType.INFO, f"Spec file detected: {spec_path}")

                    elif isinstance(message, ResultMessage):
                        if hasattr(message, "result") and message.result:
                            result_text = message.result
                            add_log(record, LogType.RESULT, message.result)
                            # Tentar extrair spec_path do resultado
                            if not spec_path:
                                spec_path = extract_spec_path(message.result)

                        # DEBUG: Log ResultMessage attributes
                        print(f"[DEBUG] ResultMessage received. Has usage: {hasattr(message, 'usage')}, usage value: {getattr(message, 'usage', 'N/A')}")

                        # Capturar token usage (usage é um dict, não objeto)
                        if hasattr(message, 'usage') and message.usage:
                            usage = message.usage
                            input_tokens = usage.get('input_tokens', 0) if isinstance(usage, dict) else 0
                            output_tokens = usage.get('output_tokens', 0) if isinstance(usage, dict) else 0
                            token_stats = {
                                "input_tokens": input_tokens,
                                "output_tokens": output_tokens,
                                "total_tokens": input_tokens + output_tokens,
                            }

                            add_log(record, LogType.INFO,
                                f"Token usage - Input: {token_stats['input_tokens']}, "
                                f"Output: {token_stats['output_tokens']}, "
                                f"Total: {token_stats['total_tokens']}")

                            if repo and execution_db:
                                await repo.update_token_usage(
                                    execution_id=execution_db.id,
                                    input_tokens=token_stats["input_tokens"],
                                    output_tokens=token_stats["output_tokens"],
                                    total_tokens=token_stats["total_tokens"],
                                    model_used=model
                                )
            except asyncio.CancelledError:
                add_log(record, LogType.ERROR, "Execution cancelled by client")
                raise

        # Mark as success
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = result_text
        add_log(record, LogType.INFO, "Plan execution completed successfully")
        if spec_path:
            add_log(record, LogType.INFO, f"Spec path: {spec_path}")

        # Atualizar status no banco se disponível (com coleta automática de métricas)
        if repo and execution_db:
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                project_id=project_id,
                result=result_text
            )
            # Busca token stats e cost stats para notificacao
            token_stats = await repo.get_token_stats_for_card(card_id)
            cost_stats = await repo.get_cost_stats_for_card(card_id)

            # Notificar via WebSocket
            await execution_ws_manager.notify_complete(
                card_id=card_id,
                status="success",
                command="/plan",
                token_stats=token_stats if token_stats.get("totalTokens", 0) > 0 else None,
                cost_stats=cost_stats if cost_stats.get("totalCost", 0) > 0 else None
            )

            # Busca execução completa para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    result=result_text,
                    logs=execution_data["logs"],
                    spec_path=spec_path,
                )

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs,
            spec_path=spec_path,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        # Atualizar status de erro no banco se disponível (com coleta automática de métricas)
        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )

            # Notificar via WebSocket
            await execution_ws_manager.notify_complete(
                card_id=card_id,
                status="error",
                command="/plan",
                error=error_message
            )

            # Busca execução para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_implement(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute /implement command with the spec file path."""
    # Detecta se é modelo Gemini
    if model.startswith("gemini"):
        return await execute_implement_gemini(
            card_id, spec_path, cwd, model, images, db_session
        )

    # Obter diretório do projeto atual do banco de dados
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            # Fallback: usar o diretório raiz do orquestrator-agent
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/implement {spec_path}"

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem  # Ex: "feature-x" de "specs/feature-x.md"

    # Usar repository se disponível, senão usar memória
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        # Criar execução no banco
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/implement",
            title=f"impl:{spec_name}"
        )
        # Log inicial no banco
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Starting implementation for: {spec_path}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Working directory: {cwd}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Prompt: {prompt}"
        )

    # Initialize execution record (memória - para compatibilidade)
    record = ExecutionRecord(
        cardId=card_id,
        title=f"impl:{spec_name}",  # Prefixo para indicar que é implement
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting implementation for: {spec_path}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        add_log(record, LogType.TEXT, block.text)
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="text",
                                content=block.text
                            )
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="tool",
                                content=f"Using tool: {block.name}"
                            )

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    add_log(record, LogType.RESULT, message.result)

                # Capturar token usage (usage é um dict, não objeto)
                if hasattr(message, 'usage') and message.usage:
                    usage = message.usage
                    input_tokens = usage.get('input_tokens', 0) if isinstance(usage, dict) else 0
                    output_tokens = usage.get('output_tokens', 0) if isinstance(usage, dict) else 0
                    token_stats = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    }

                    add_log(record, LogType.INFO,
                        f"Token usage - Input: {token_stats['input_tokens']}, "
                        f"Output: {token_stats['output_tokens']}, "
                        f"Total: {token_stats['total_tokens']}")

                    if repo and execution_db:
                        await repo.update_token_usage(
                            execution_id=execution_db.id,
                            input_tokens=token_stats["input_tokens"],
                            output_tokens=token_stats["output_tokens"],
                            total_tokens=token_stats["total_tokens"],
                            model_used=model
                        )

        # Mark as success
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = result_text
        add_log(record, LogType.INFO, "Implementation completed successfully")

        # Atualizar status no banco se disponível (com coleta automática de métricas)
        if repo and execution_db:
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                project_id=project_id,
                result=result_text
            )
            # Busca token stats e cost stats para notificacao
            token_stats = await repo.get_token_stats_for_card(card_id)
            cost_stats = await repo.get_cost_stats_for_card(card_id)

            # Notificar via WebSocket
            await execution_ws_manager.notify_complete(
                card_id=card_id,
                status="success",
                command="/implement",
                token_stats=token_stats if token_stats.get("totalTokens", 0) > 0 else None,
                cost_stats=cost_stats if cost_stats.get("totalCost", 0) > 0 else None
            )

            # Busca execução completa para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    result=result_text,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        # Atualizar status de erro no banco se disponível (com coleta automática de métricas)
        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )

            # Notificar via WebSocket
            await execution_ws_manager.notify_complete(
                card_id=card_id,
                status="error",
                command="/implement",
                error=error_message
            )

            # Busca execução para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def create_fix_card_for_test_failure(
    card_id: str,
    logs: list[ExecutionLog],
    spec_path: str,
    execution_error: Optional[str] = None
) -> Optional[str]:
    """Create a fix card when tests fail."""
    from .database import async_session_maker
    from .repositories.card_repository import CardRepository
    from .services.test_result_analyzer import TestResultAnalyzer

    try:
        # Analyze the test failure
        analyzer = TestResultAnalyzer()
        error_info = analyzer.analyze_test_failure(logs)

        # Add execution error if present
        if execution_error:
            error_info["error_messages"].insert(0, f"Execution error: {execution_error}")
            if not error_info["error_type"]:
                error_info["error_type"] = "execution_error"

        # Generate description for the fix card
        description = analyzer.generate_fix_description(error_info)

        # Extract context for storage
        context = analyzer.extract_error_context(logs)

        async with async_session_maker() as session:
            repo = CardRepository(session)

            # Check if there's already an active fix card
            existing_fix = await repo.get_active_fix_card(card_id)
            if existing_fix:
                print(f"[{card_id[:8]}] Fix card already exists: {existing_fix.id}")
                return existing_fix.id

            # Create the fix card
            fix_card = await repo.create_fix_card(
                card_id,
                {
                    "description": description,
                    "context": context
                }
            )

            if fix_card:
                await session.commit()
                print(f"[{card_id[:8]}] Created fix card: {fix_card.id}")
                return fix_card.id
            else:
                print(f"[{card_id[:8]}] Failed to create fix card")
                return None

    except Exception as e:
        print(f"[{card_id[:8]}] Error creating fix card: {e}")
        return None


async def execute_test_implementation(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute /test-implementation command with the spec file path."""
    # Detecta se é modelo Gemini
    if model.startswith("gemini"):
        return await execute_test_implementation_gemini(
            card_id, spec_path, cwd, model, images, db_session
        )

    # Obter diretório do projeto atual do banco de dados
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            # Fallback: usar o diretório raiz do orquestrator-agent
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/test-implementation {spec_path}"

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem  # Ex: "feature-x" de "specs/feature-x.md"

    # Usar repository se disponível, senão usar memória
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        # Criar execução no banco
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/test-implementation",
            title=f"test:{spec_name}"
        )
        # Log inicial no banco
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Starting test-implementation for: {spec_path}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Working directory: {cwd}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Prompt: {prompt}"
        )

    # Initialize execution record (memória - para compatibilidade)
    record = ExecutionRecord(
        cardId=card_id,
        title=f"test:{spec_name}",  # Prefixo para indicar que é test
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting test-implementation for: {spec_path}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        add_log(record, LogType.TEXT, block.text)
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="text",
                                content=block.text
                            )
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="tool",
                                content=f"Using tool: {block.name}"
                            )

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    add_log(record, LogType.RESULT, message.result)

                # Capturar token usage (usage é um dict, não objeto)
                if hasattr(message, 'usage') and message.usage:
                    usage = message.usage
                    input_tokens = usage.get('input_tokens', 0) if isinstance(usage, dict) else 0
                    output_tokens = usage.get('output_tokens', 0) if isinstance(usage, dict) else 0
                    token_stats = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    }

                    add_log(record, LogType.INFO,
                        f"Token usage - Input: {token_stats['input_tokens']}, "
                        f"Output: {token_stats['output_tokens']}, "
                        f"Total: {token_stats['total_tokens']}")

                    if repo and execution_db:
                        await repo.update_token_usage(
                            execution_id=execution_db.id,
                            input_tokens=token_stats["input_tokens"],
                            output_tokens=token_stats["output_tokens"],
                            total_tokens=token_stats["total_tokens"],
                            model_used=model
                        )

        # Check if tests failed based on logs
        test_failed = False
        for log in record.logs:
            if log.type == LogType.ERROR or (
                log.type in [LogType.TEXT, LogType.RESULT] and
                any(indicator in log.content.lower() for indicator in [
                    "test failed", "tests failed", "failed test",
                    "assertion error", "✗", "error:", "failed:"
                ])
            ):
                test_failed = True
                break

        # Mark as success or failure based on test results
        record.completed_at = datetime.now().isoformat()

        if test_failed:
            record.status = ExecutionStatus.ERROR
            add_log(record, LogType.ERROR, "Tests failed - creating fix card")

            # Atualizar status de erro no banco se disponível (com coleta automática de métricas)
            if repo and execution_db:
                await repo.add_log(
                    execution_id=execution_db.id,
                    log_type="error",
                    content="Tests failed - creating fix card"
                )
                await repo.update_execution_status_with_metrics(
                    execution_id=execution_db.id,
                    status=DBExecutionStatus.ERROR,
                    project_id=project_id,
                    result="Tests failed"
                )

                # Notificar via WebSocket
                await execution_ws_manager.notify_complete(
                    card_id=card_id,
                    status="error",
                    command="/test-implementation",
                    error="Tests failed"
                )

            # Analyze test failure and create fix card
            fix_card_id = await create_fix_card_for_test_failure(card_id, record.logs, spec_path)

            # Busca execução para retornar logs
            if repo and execution_db:
                execution_data = await repo.get_execution_with_logs(card_id)
                if execution_data:
                    return PlanResult(
                        success=False,
                        error="Tests failed. A fix card has been created automatically.",
                        logs=execution_data["logs"],
                        fix_card_created=True if fix_card_id else False,
                        fix_card_id=fix_card_id
                    )

            return PlanResult(
                success=False,
                error="Tests failed. A fix card has been created automatically.",
                logs=record.logs,
                fix_card_created=True if fix_card_id else False,
                fix_card_id=fix_card_id
            )
        else:
            record.status = ExecutionStatus.SUCCESS
            record.result = result_text
            add_log(record, LogType.INFO, "Test-implementation completed successfully")

            # Atualizar status no banco se disponível (com coleta automática de métricas)
            if repo and execution_db:
                await repo.update_execution_status_with_metrics(
                    execution_id=execution_db.id,
                    status=DBExecutionStatus.SUCCESS,
                    project_id=project_id,
                    result=result_text
                )
                # Busca token stats e cost stats para notificacao
                token_stats = await repo.get_token_stats_for_card(card_id)
                cost_stats = await repo.get_cost_stats_for_card(card_id)

                # Notificar via WebSocket
                await execution_ws_manager.notify_complete(
                    card_id=card_id,
                    status="success",
                    command="/test-implementation",
                    token_stats=token_stats if token_stats.get("totalTokens", 0) > 0 else None,
                    cost_stats=cost_stats if cost_stats.get("totalCost", 0) > 0 else None
                )

                # Busca execução completa para retornar logs
                execution_data = await repo.get_execution_with_logs(card_id)
                if execution_data:
                    return PlanResult(
                        success=True,
                        result=result_text,
                        logs=execution_data["logs"],
                    )

            return PlanResult(
                success=True,
                result=result_text,
                logs=record.logs,
            )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        # Atualizar status de erro no banco se disponível (com coleta automática de métricas)
        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )

            # Notificar via WebSocket
            await execution_ws_manager.notify_complete(
                card_id=card_id,
                status="error",
                command="/test-implementation",
                error=error_message
            )

        # Create fix card for execution errors as well
        fix_card_id = await create_fix_card_for_test_failure(
            card_id,
            record.logs,
            spec_path,
            execution_error=error_message
        )

        # Busca execução para retornar logs
        if repo and execution_db:
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                    fix_card_created=True if fix_card_id else False,
                    fix_card_id=fix_card_id
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
            fix_card_created=True if fix_card_id else False,
            fix_card_id=fix_card_id
        )


async def execute_review(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute /review command with the spec file path."""
    # Detecta se é modelo Gemini
    if model.startswith("gemini"):
        return await execute_review_gemini(
            card_id, spec_path, cwd, model, images, db_session
        )

    # Obter diretório do projeto atual do banco de dados
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Initial cwd parameter: {cwd}")

    # Variável para armazenar project_id para métricas
    project_id = None

    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            project_id = active_project.id
            print(f"[Agent] Found active project: {project_path}")
        else:
            # Fallback: usar o diretório raiz do orquestrator-agent
            project_path = str(Path(__file__).parent.parent.parent)
            project_id = "default-project"
            print(f"[Agent] No active project, using root project: {project_path}")

        # Obter worktree para isolamento
        cwd, branch_name, worktree_path = await get_worktree_cwd(
            card_id, project_path, session
        )
        if worktree_path:
            print(f"[Agent] Using worktree isolation: {cwd}")
        else:
            print(f"[Agent] Using project directory (no worktree): {cwd}")

    # Mapear nome de modelo para valor do SDK
    model_map = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    sdk_model = model_map.get(model, "opus")

    prompt = f"/review {spec_path}"

    # Add image references if available
    if images:
        prompt += "\n\nImagens anexadas neste card:\n"
        for img in images:
            prompt += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Usar spec_path como "título" para contexto visual
    spec_name = Path(spec_path).stem  # Ex: "feature-x" de "specs/feature-x.md"

    # Usar repository se disponível, senão usar memória
    repo = None
    execution_db = None

    if db_session:
        repo = ExecutionRepository(db_session)
        # Criar execução no banco
        execution_db = await repo.create_execution(
            card_id=card_id,
            command="/review",
            title=f"review:{spec_name}"
        )
        # Log inicial no banco
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Starting review for: {spec_path}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Working directory: {cwd}"
        )
        await repo.add_log(
            execution_id=execution_db.id,
            log_type="info",
            content=f"Prompt: {prompt}"
        )

    # Initialize execution record (memória - para compatibilidade)
    record = ExecutionRecord(
        cardId=card_id,
        title=f"review:{spec_name}",  # Prefixo para indicar que é review
        startedAt=datetime.now().isoformat(),
        status=ExecutionStatus.RUNNING,
        logs=[],
    )
    executions[card_id] = record

    add_log(record, LogType.INFO, f"Starting review for: {spec_path}")
    add_log(record, LogType.INFO, f"Working directory: {cwd}")
    add_log(record, LogType.INFO, f"Prompt: {prompt}")

    result_text = ""

    try:
        # Configure agent options
        options = ClaudeAgentOptions(
            cwd=Path(cwd),
            setting_sources=["user", "project"],
            allowed_tools=["Skill", "Read", "Write", "Edit", "Bash", "Glob", "Grep", "TodoWrite"],
            permission_mode="acceptEdits",
            model=sdk_model,
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        add_log(record, LogType.TEXT, block.text)
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="text",
                                content=block.text
                            )
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        add_log(record, LogType.TOOL, f"Using tool: {block.name}")
                        # Salva log no banco se disponível
                        if repo and execution_db:
                            await repo.add_log(
                                execution_id=execution_db.id,
                                log_type="tool",
                                content=f"Using tool: {block.name}"
                            )

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
                    add_log(record, LogType.RESULT, message.result)

                # Capturar token usage (usage é um dict, não objeto)
                if hasattr(message, 'usage') and message.usage:
                    usage = message.usage
                    input_tokens = usage.get('input_tokens', 0) if isinstance(usage, dict) else 0
                    output_tokens = usage.get('output_tokens', 0) if isinstance(usage, dict) else 0
                    token_stats = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                    }

                    add_log(record, LogType.INFO,
                        f"Token usage - Input: {token_stats['input_tokens']}, "
                        f"Output: {token_stats['output_tokens']}, "
                        f"Total: {token_stats['total_tokens']}")

                    if repo and execution_db:
                        await repo.update_token_usage(
                            execution_id=execution_db.id,
                            input_tokens=token_stats["input_tokens"],
                            output_tokens=token_stats["output_tokens"],
                            total_tokens=token_stats["total_tokens"],
                            model_used=model
                        )

        # Mark as success
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.SUCCESS
        record.result = result_text
        add_log(record, LogType.INFO, "Review completed successfully")

        # Atualizar status no banco se disponível (com coleta automática de métricas)
        if repo and execution_db:
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.SUCCESS,
                project_id=project_id,
                result=result_text
            )
            # Busca token stats e cost stats para notificacao
            token_stats = await repo.get_token_stats_for_card(card_id)
            cost_stats = await repo.get_cost_stats_for_card(card_id)

            # Notificar via WebSocket
            await execution_ws_manager.notify_complete(
                card_id=card_id,
                status="success",
                command="/review",
                token_stats=token_stats if token_stats.get("totalTokens", 0) > 0 else None,
                cost_stats=cost_stats if cost_stats.get("totalCost", 0) > 0 else None
            )

            # Busca execução completa para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=True,
                    result=result_text,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=True,
            result=result_text,
            logs=record.logs,
        )

    except Exception as e:
        error_message = str(e)
        record.completed_at = datetime.now().isoformat()
        record.status = ExecutionStatus.ERROR
        record.result = error_message
        add_log(record, LogType.ERROR, f"Execution error: {error_message}")

        # Atualizar status de erro no banco se disponível (com coleta automática de métricas)
        if repo and execution_db:
            await repo.add_log(
                execution_id=execution_db.id,
                log_type="error",
                content=error_message
            )
            await repo.update_execution_status_with_metrics(
                execution_id=execution_db.id,
                status=DBExecutionStatus.ERROR,
                project_id=project_id,
                result=error_message
            )

            # Notificar via WebSocket
            await execution_ws_manager.notify_complete(
                card_id=card_id,
                status="error",
                command="/review",
                error=error_message
            )

            # Busca execução para retornar logs
            execution_data = await repo.get_execution_with_logs(card_id)
            if execution_data:
                return PlanResult(
                    success=False,
                    error=error_message,
                    logs=execution_data["logs"],
                )

        return PlanResult(
            success=False,
            error=error_message,
            logs=record.logs,
        )


async def execute_expert_triage(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    db_session: Optional[AsyncSession] = None,
) -> dict:
    """
    Execute /expert-triage command using Claude Agent SDK.

    This uses AI reasoning (not keywords) to identify relevant experts
    based on the card's title and description.

    Returns:
        dict with keys: success, experts, error (optional)
    """
    from .database import async_session_maker
    from .models.project import ActiveProject
    from sqlalchemy import select

    print(f"[Agent] Starting expert triage for card: {card_id[:8]}")

    # Get project path
    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        active_project = result.scalar_one_or_none()
        if active_project:
            project_path = active_project.path
            print(f"[Agent] Found active project: {project_path}")
        else:
            project_path = str(Path(__file__).parent.parent.parent)
            print(f"[Agent] No active project, using root project: {project_path}")

    # Build prompt with arguments
    # Format: <cardId> <title> [description]
    prompt = f"/expert-triage {card_id} {title}"
    if description:
        prompt += f" {description}"

    # NOTE: Triage não cria execution separada no banco
    # Os logs do triage serão incluídos na execution do /plan
    # Isso evita race condition onde a UI mostra status do triage em vez do plan

    print(f"[Agent] Expert triage for: {title[:50]}")
    print(f"[Agent] Working directory: {project_path}")

    result_text = ""

    try:
        # Configure agent options - use haiku for speed
        options = ClaudeAgentOptions(
            cwd=Path(project_path),
            setting_sources=["user", "project"],
            allowed_tools=["Read", "Glob"],
            permission_mode="acceptEdits",
            model="haiku",
        )

        # Execute using claude-agent-sdk
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"[Agent] [TRIAGE] {block.text[:100]}...")
                        result_text += block.text + "\n"
                    elif isinstance(block, ToolUseBlock):
                        print(f"[Agent] [TRIAGE] Using tool: {block.name}")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    result_text = message.result

        # Parse JSON from result
        experts = {}
        try:
            # Find JSON block in result
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result_text)
            if json_match:
                json_str = json_match.group(1)
                parsed = json.loads(json_str)
                experts = parsed.get("experts", {})
                print(f"[Agent] Identified {len(experts)} experts via AI")
            else:
                # Try to parse entire result as JSON
                parsed = json.loads(result_text.strip())
                experts = parsed.get("experts", {})
                print(f"[Agent] Identified {len(experts)} experts via AI")
        except json.JSONDecodeError as e:
            print(f"[Agent] Failed to parse triage JSON: {e}")
            # Return empty experts on parse error
            experts = {}

        print(f"[Agent] Expert triage completed successfully")

        return {
            "success": True,
            "cardId": card_id,
            "experts": experts,
        }

    except Exception as e:
        error_message = str(e)
        print(f"[Agent] Expert triage error: {error_message}")

        return {
            "success": False,
            "cardId": card_id,
            "experts": {},
            "error": error_message,
        }
