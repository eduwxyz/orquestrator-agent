# Adicionar Modelos Gemini ao Sistema de Cards do Kanban

## 1. Resumo

Adicionar suporte aos modelos Google Gemini (gemini-3-pro e gemini-3-flash) como opções de execução para cards no kanban, permitindo que cada etapa do workflow (plan, implement, test, review) possa ser executada com modelos Gemini, similar à implementação existente no chat.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar gemini-3-pro e gemini-3-flash como opções de modelo no modal de criação de cards
- [x] Implementar integração com API do Gemini no backend para execução de cards
- [x] Reutilizar lógica de requisição do chat para manter consistência
- [x] Permitir seleção de modelos Gemini para cada etapa do workflow (plan, implement, test, review)
- [x] Manter retrocompatibilidade com cards existentes usando modelos Claude

### Fora do Escopo
- Migração automática de cards existentes para modelos Gemini
- Modificação da interface de chat (já implementado)
- Alteração no sistema de autenticação/API keys

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/types/index.ts` | Modificar | Expandir ModelType para incluir modelos Gemini |
| `frontend/src/components/AddCardModal/AddCardModal.tsx` | Modificar | Adicionar cards de seleção para modelos Gemini |
| `backend/src/schemas/card.py` | Modificar | Atualizar ModelType para incluir Gemini |
| `backend/src/models/card.py` | Modificar | Garantir que campos de modelo aceitem valores Gemini |
| `backend/src/services/gemini_service.py` | Criar | Serviço para integração com API Gemini |
| `backend/src/agent.py` | Modificar | Adicionar suporte para execução com modelos Gemini |
| `backend/src/agent_gemini.py` | Criar | Implementação específica para Gemini com plan.toml |
| `backend/.env.example` | Modificar | Adicionar GEMINI_API_KEY |

### Detalhes Técnicos

#### 1. Atualização de Tipos (Frontend)

**`frontend/src/types/index.ts`**
```typescript
// Expandir ModelType para incluir modelos Gemini
export type ModelType =
  | 'opus-4.5'
  | 'sonnet-4.5'
  | 'haiku-4.5'
  | 'gemini-3-pro'
  | 'gemini-3-flash';

// Adicionar provider info para UI
export interface ModelInfo {
  value: ModelType;
  label: string;
  provider: 'anthropic' | 'google';
  tagline: string;
  performance: string;
  icon: string;
  accent: string;
}
```

#### 2. Modal de Criação - Adicionar Modelos Gemini

**`frontend/src/components/AddCardModal/AddCardModal.tsx`**
```typescript
const MODEL_CARDS: ModelCardData[] = [
  // Modelos existentes Claude...
  {
    value: 'opus-4.5',
    label: 'Opus 4.5',
    provider: 'anthropic',
    tagline: 'Maximum intelligence',
    performance: 'Highest Quality',
    icon: '◈',
    accent: 'opus'
  },
  // ... sonnet-4.5, haiku-4.5

  // Novos modelos Gemini
  {
    value: 'gemini-3-pro',
    label: 'Gemini Pro',
    provider: 'google',
    tagline: 'Advanced reasoning',
    performance: 'High Performance',
    icon: '🔷',
    accent: 'gemini-pro'
  },
  {
    value: 'gemini-3-flash',
    label: 'Gemini Flash',
    provider: 'google',
    tagline: 'Fast responses',
    performance: 'Quick & Efficient',
    icon: '⚡',
    accent: 'gemini-flash'
  }
];

// Adicionar estilos CSS para badges Google
const getProviderBadge = (provider: string) => {
  switch(provider) {
    case 'anthropic': return '🔺 Anthropic';
    case 'google': return '🔷 Google';
    default: return '';
  }
};
```

#### 3. Backend - Schema Update

**`backend/src/schemas/card.py`**
```python
from typing import Literal

# Expandir ModelType
ModelType = Literal[
    "opus-4.5",
    "sonnet-4.5",
    "haiku-4.5",
    "gemini-3-pro",
    "gemini-3-flash"
]
```

#### 4. Serviço Gemini

**`backend/src/services/gemini_service.py`**
```python
import os
import google.generativeai as genai
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional
import toml

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=self.api_key)

    def _get_plan_context(self, cwd: str) -> str:
        """Read plan.toml if exists and format as context"""
        plan_path = Path(cwd) / "plan.toml"
        if not plan_path.exists():
            return ""

        try:
            plan_data = toml.load(plan_path)
            context = "\n# Project Configuration (plan.toml)\n"
            for key, value in plan_data.items():
                context += f"{key}: {value}\n"
            return context
        except Exception as e:
            print(f"Error reading plan.toml: {e}")
            return ""

    def _get_model(self, model_name: str):
        """Map our model names to Gemini model names"""
        model_map = {
            "gemini-3-pro": "gemini-1.5-pro",
            "gemini-3-flash": "gemini-1.5-flash"
        }
        return genai.GenerativeModel(model_map.get(model_name, "gemini-1.5-pro"))

    async def execute_command(
        self,
        command: str,  # /plan, /implement, /test, /review
        content: str,
        model_name: str,
        cwd: str,
        images: Optional[list] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a command using Gemini API"""

        # Get plan.toml context
        plan_context = self._get_plan_context(cwd)

        # Build the prompt with plan.toml context
        full_prompt = f"""
{plan_context}

You are an AI assistant helping with software development tasks.
Current working directory: {cwd}

Command: {command}
{content}
"""

        # Get the appropriate model
        model = self._get_model(model_name)

        # Generate response
        try:
            response = await model.generate_content_async(
                full_prompt,
                stream=True
            )

            async for chunk in response:
                if chunk.text:
                    yield {
                        "type": "text",
                        "content": chunk.text
                    }

        except Exception as e:
            yield {
                "type": "error",
                "content": f"Gemini API error: {str(e)}"
            }
```

#### 5. Integração no Agent

**`backend/src/agent_gemini.py`**
```python
"""
Gemini-specific agent implementation for card execution
"""
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from .services.gemini_service import GeminiService
from .models.execution_result import PlanResult, ImplementResult, TestResult, ReviewResult

class GeminiAgent:
    def __init__(self):
        self.gemini_service = GeminiService()

    async def execute_plan(
        self,
        card_id: str,
        title: str,
        description: str,
        cwd: str,
        model: str,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> PlanResult:
        """Execute plan phase using Gemini"""

        command = "/plan"
        content = f"{title}: {description}"

        logs = []
        result_text = ""
        spec_path = None

        async for chunk in self.gemini_service.execute_command(
            command=command,
            content=content,
            model_name=model,
            cwd=cwd,
            images=images
        ):
            if chunk["type"] == "text":
                result_text += chunk["content"]
                logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "text",
                    "content": chunk["content"]
                })
            elif chunk["type"] == "error":
                logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "error",
                    "content": chunk["content"]
                })
                return PlanResult(
                    success=False,
                    result=chunk["content"],
                    logs=logs,
                    spec_path=None
                )

        # Parse result to find spec file path
        if "specs/" in result_text:
            import re
            match = re.search(r'specs/[\w-]+\.md', result_text)
            if match:
                spec_path = match.group(0)

        return PlanResult(
            success=True,
            result=result_text,
            logs=logs,
            spec_path=spec_path
        )

    async def execute_implement(
        self,
        card_id: str,
        spec_path: str,
        cwd: str,
        model: str,
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> ImplementResult:
        """Execute implement phase using Gemini"""

        # Read spec file
        spec_full_path = Path(cwd) / spec_path
        if not spec_full_path.exists():
            return ImplementResult(
                success=False,
                result=f"Spec file not found: {spec_path}",
                logs=[],
            )

        spec_content = spec_full_path.read_text()

        command = "/implement"
        content = f"Implement the following specification:\n\n{spec_content}"

        # Similar implementation as execute_plan...
        # [implementation details]

    # Similar methods for execute_test and execute_review
```

#### 6. Modificação do Agent Principal

**`backend/src/agent.py`**
```python
from .agent_gemini import GeminiAgent

# Adicionar detecção de provider
def get_model_provider(model: str) -> str:
    """Determine provider from model name"""
    if model.startswith("gemini"):
        return "google"
    return "anthropic"

async def execute_plan(
    card_id: str,
    title: str,
    description: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[List[Dict[str, Any]]] = None,
    db_session: Optional[AsyncSession] = None,
) -> PlanResult:
    """Execute a plan using appropriate AI provider"""

    provider = get_model_provider(model)

    if provider == "google":
        # Use Gemini implementation
        gemini_agent = GeminiAgent()
        return await gemini_agent.execute_plan(
            card_id=card_id,
            title=title,
            description=description,
            cwd=cwd,
            model=model,
            images=images
        )
    else:
        # Existing Claude implementation
        # ... código existente ...
```

#### 7. Variáveis de Ambiente

**`backend/.env.example`**
```bash
# Existing variables...
ANTHROPIC_API_KEY=your_anthropic_key_here

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 4. Testes

### Unitários
- [ ] Teste GeminiService com mock da API
- [ ] Teste mapeamento de modelos (gemini-3-pro → gemini-1.5-pro)
- [ ] Teste leitura e parsing do plan.toml
- [ ] Teste detecção de provider (get_model_provider)

### Integração
- [ ] Criar card com modelo Gemini e executar workflow completo
- [ ] Testar fallback quando GEMINI_API_KEY não está configurada
- [ ] Verificar que cards existentes com Claude continuam funcionando
- [ ] Testar execução mista (ex: Plan com Claude, Implement com Gemini)

### E2E
- [ ] Fluxo completo: criar card com Gemini → executar todas as etapas
- [ ] Verificar persistência correta dos modelos no banco
- [ ] Testar UI: seleção de modelos, badges de provider, visual feedback

---

## 5. Considerações

### Riscos
- **API Key Management:** Garantir que GEMINI_API_KEY seja validada no startup
- **Rate Limiting:** Implementar retry logic para limites da API Gemini
- **Custo:** Modelos Gemini podem ter custos diferentes dos Claude

### Dependências
- Biblioteca `google-generativeai` precisa ser adicionada ao requirements.txt
- Necessário obter GEMINI_API_KEY do Google Cloud Console

### Migração
- Cards existentes continuarão usando modelos Claude
- Novos cards poderão escolher entre Claude ou Gemini
- Considerar adicionar configuração de modelo padrão por projeto

### Melhorias Futuras
- Cache de respostas para reduzir custos
- Métricas de performance comparando providers
- Suporte a mais modelos (GPT-4, Llama, etc.)