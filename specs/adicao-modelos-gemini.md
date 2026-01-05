# Adição de Modelos da Família Gemini

## 1. Resumo

Implementação do suporte aos modelos da família Gemini (Google) como opção de IA no produto, tanto no kanban quanto no recurso de chat. A integração será feita através do Gemini CLI via subprocess, com conversão dos comandos existentes de formato .md para .toml para compatibilidade.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Converter todos os comandos existentes de .md para formato .toml
- [x] Adicionar configuração para integração com Gemini CLI
- [x] Implementar suporte a modelos Gemini no backend (agent e chat)
- [x] Adicionar modelos Gemini na interface do usuário (seletor de modelos)
- [x] Manter compatibilidade com Claude SDK para comandos existentes
- [x] Criar estrutura .gemini/commands com comandos em formato .toml

### Fora do Escopo
- Migração completa do Claude SDK para Gemini CLI
- Remoção do suporte aos modelos Claude/OpenAI existentes
- Modificação da estrutura de banco de dados

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `.gemini/commands/plan.toml` | Criar | Comando /plan em formato TOML para Gemini |
| `.gemini/commands/implement.toml` | Criar | Comando /implement em formato TOML |
| `.gemini/commands/test-implementation.toml` | Criar | Comando /test-implementation em formato TOML |
| `.gemini/commands/review.toml` | Criar | Comando /review em formato TOML |
| `.gemini/commands/question.toml` | Criar | Comando /question em formato TOML |
| `.gemini/commands/dev-workflow.toml` | Criar | Comando /dev-workflow em formato TOML |
| `backend/src/gemini_agent.py` | Criar | Classe para integração com Gemini CLI |
| `backend/src/agent.py` | Modificar | Adicionar suporte para escolha entre Claude e Gemini |
| `backend/src/agent_chat.py` | Modificar | Adicionar suporte para chat com Gemini |
| `backend/src/schemas/card.py` | Modificar | Adicionar tipos de modelo Gemini |
| `frontend/src/components/Chat/ModelSelector.tsx` | Modificar | Adicionar modelos Gemini na lista |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos TypeScript para modelos Gemini |
| `backend/requirements.txt` | Modificar | Adicionar dependências necessárias |

### Detalhes Técnicos

#### 1. Formato TOML para Comandos

Estrutura base para conversão de comandos .md para .toml:

```toml
# .gemini/commands/plan.toml
[metadata]
name = "plan"
description = "Cria planos de implementação detalhados para features, bugs ou refatorações"
argument_hint = "[descrição da tarefa]"
model = "gemini-1.5-pro"
allowed_tools = ["Read", "Glob", "Grep", "Write", "Task"]

[prompt]
content = """
# Plan

Crie um plano de implementação detalhado com base na solicitação do usuário: {ARGUMENTS}

Salve o planejamento em `specs/<nome_descritivo>.md`

## Instruções

1. Se `{ARGUMENTS}` estiver vazio, pergunte ao usuário o que deseja implementar
2. Analise toda a codebase para entender padrões existentes
3. Gere um nome descritivo e curto para o arquivo
4. Inclua snippets de código quando fizer sentido
5. Identifique o tipo de tarefa (feature, bug, refactor, etc.)

[Resto do conteúdo do comando...]
"""
```

#### 2. Classe GeminiAgent

```python
# backend/src/gemini_agent.py
import subprocess
import json
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any

class GeminiAgent:
    """Handler para integração com Gemini CLI"""

    def __init__(self, model: str = "gemini-1.5-pro"):
        self.model = model
        self.gemini_cli_path = "gemini"  # Assumindo que está no PATH

    async def execute_command(
        self,
        command: str,
        arguments: str,
        cwd: Optional[Path] = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Executa um comando usando Gemini CLI via subprocess.

        Args:
            command: Nome do comando (ex: "plan", "implement")
            arguments: Argumentos do comando
            cwd: Diretório de trabalho
            stream: Se deve fazer streaming da resposta
        """
        # Monta o comando completo
        cmd_parts = [
            self.gemini_cli_path,
            "run",
            f"--command={command}",
            f"--model={self.model}",
        ]

        if cwd:
            cmd_parts.extend(["--cwd", str(cwd)])

        # Adiciona argumentos
        cmd_parts.append(arguments)

        # Executa o processo
        process = await asyncio.create_subprocess_exec(
            *cmd_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd
        )

        if stream:
            # Stream output line by line
            async for line in process.stdout:
                yield line.decode('utf-8')
        else:
            # Retorna output completo
            stdout, stderr = await process.communicate()
            if stderr:
                raise RuntimeError(f"Gemini CLI error: {stderr.decode('utf-8')}")
            yield stdout.decode('utf-8')

    async def chat_completion(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Realiza chat completion usando Gemini.
        """
        # Formata mensagens para o formato esperado pelo Gemini
        formatted_prompt = self._format_messages(messages, system_prompt)

        # Usa comando question para chat
        async for chunk in self.execute_command(
            command="question",
            arguments=formatted_prompt,
            stream=True
        ):
            yield chunk

    def _format_messages(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None
    ) -> str:
        """Formata mensagens para o formato do Gemini"""
        parts = []

        if system_prompt:
            parts.append(f"System: {system_prompt}\n")

        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            parts.append(f"{role}: {msg['content']}\n")

        return "\n".join(parts)
```

#### 3. Integração no Agent Principal

```python
# Modificações em backend/src/agent.py

async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute a plan using Claude Agent SDK or Gemini CLI."""

    # Detecta se é modelo Gemini
    if model.startswith("gemini"):
        return await execute_plan_gemini(
            card_id, title, description, cwd, model, images, db_session
        )

    # Código existente para Claude...

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

    gemini = GeminiAgent(model=model)

    # Prepara argumentos
    arguments = f"{title}: {description}"
    if images:
        arguments += "\n\nImagens anexadas:\n"
        for img in images:
            arguments += f"- {img.get('filename', 'image')}: {img.get('path', '')}\n"

    # Executa comando via Gemini CLI
    full_response = ""
    async for chunk in gemini.execute_command(
        command="plan",
        arguments=arguments,
        cwd=Path(cwd),
        stream=True
    ):
        full_response += chunk
        # Log no banco/memória...

    # Extrai spec_path e retorna resultado
    spec_path = extract_spec_path(full_response)
    return PlanResult(
        success=True,
        spec_path=spec_path,
        result=full_response
    )
```

#### 4. Modelos Gemini no Frontend

```typescript
// Adicionar em frontend/src/components/Chat/ModelSelector.tsx

export const AVAILABLE_MODELS: AIModel[] = [
  // ... modelos existentes ...

  // Modelos Gemini
  {
    id: 'gemini-1.5-pro',
    name: 'Gemini 1.5 Pro',
    displayName: 'Gemini Pro',
    provider: 'google',
    maxTokens: 1000000,
    description: 'Google\'s most capable multimodal model with long context',
    performance: 'powerful',
    icon: '🌟',
    accent: 'google',
    badge: 'Long Context'
  },
  {
    id: 'gemini-1.5-flash',
    name: 'Gemini 1.5 Flash',
    displayName: 'Gemini Flash',
    provider: 'google',
    maxTokens: 1000000,
    description: 'Fast and efficient model for quick tasks',
    performance: 'fastest',
    icon: '⚡',
    accent: 'google'
  },
  {
    id: 'gemini-1.0-pro',
    name: 'Gemini 1.0 Pro',
    displayName: 'Gemini 1.0',
    provider: 'google',
    maxTokens: 32000,
    description: 'Balanced model for general tasks',
    performance: 'balanced',
    icon: '💎',
    accent: 'google'
  }
];
```

#### 5. Atualização dos Tipos

```python
# backend/src/schemas/card.py
ModelType = Literal[
    "opus-4.5", "sonnet-4.5", "haiku-4.5",  # Claude
    "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.0-pro"  # Gemini
]
```

---

## 4. Testes

### Unitários
- [ ] Teste da classe GeminiAgent com mocks do subprocess (Pendente - requer instalação do Gemini CLI)
- [ ] Teste de conversão de mensagens para formato Gemini (Pendente - requer instalação do Gemini CLI)
- [ ] Teste de detecção de tipo de modelo (Claude vs Gemini) (Pendente - requer instalação do Gemini CLI)
- [ ] Teste de parsing de comandos TOML (Pendente - requer instalação do Gemini CLI)

### Integração
- [ ] Teste de execução de comando /plan via Gemini CLI (Pendente - requer instalação do Gemini CLI)
- [ ] Teste de chat completion com Gemini (Pendente - requer instalação do Gemini CLI)
- [ ] Teste de seleção de modelo Gemini no frontend (Pendente - requer instalação do Gemini CLI)
- [ ] Teste end-to-end de workflow com modelo Gemini (Pendente - requer instalação do Gemini CLI)

---

## 5. Considerações

- **Riscos:**
  - Dependência do Gemini CLI estar instalado e configurado no sistema
  - Possíveis diferenças de comportamento entre Claude SDK e Gemini CLI
  - Latência adicional devido ao uso de subprocess

- **Dependências:**
  - Gemini CLI deve estar instalado e acessível no PATH
  - Credenciais do Google/Gemini devem estar configuradas
  - Conversão manual dos comandos pode introduzir erros de sintaxe TOML

- **Mitigações:**
  - Implementar fallback para Claude se Gemini CLI não estiver disponível
  - Validar arquivos TOML após conversão
  - Adicionar cache de respostas para reduzir chamadas repetitivas
  - Documentar processo de instalação e configuração do Gemini CLI