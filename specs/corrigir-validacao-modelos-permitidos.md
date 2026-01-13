# Corrigir Validação de Modelos Permitidos

## 1. Resumo

Correção da validação de modelos de IA no sistema para garantir que apenas os modelos especificados sejam aceitos (opus-4.5, sonnet-4.5, haiku-4.5, gemini-3.0-pro, gemini-3.0-flash), removendo modelos legados e corrigindo nomenclaturas inconsistentes. O sistema atualmente aceita 8 modelos diferentes incluindo modelos legados do Claude 3 e usa nomenclaturas incorretas para modelos Gemini (gemini-3-pro ao invés de gemini-3.0-pro).

---

## 2. Objetivos e Escopo

### Objetivos
- [ ] Remover modelos legados (claude-3-sonnet, claude-3-opus, gpt-4-turbo) de todos os seletores
- [ ] Corrigir nomenclaturas dos modelos Gemini (gemini-3-pro → gemini-3.0-pro, gemini-3-flash → gemini-3.0-flash)
- [ ] Atualizar validação no backend para aceitar apenas os 5 modelos permitidos
- [ ] Garantir consistência de nomenclatura entre frontend, backend e banco de dados
- [ ] Atualizar mapeamento de modelos para APIs externas com as novas nomenclaturas

### Fora do Escopo
- Adicionar novos modelos além dos especificados
- Modificar preços dos modelos existentes
- Alterar o modelo padrão (continuará sendo opus-4.5 para cards e sonnet-4.5 para chat)

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/types/index.ts` | Modificar | Atualizar tipo `ModelType` com nomenclaturas corretas |
| `frontend/src/components/Chat/ModelSelector.tsx` | Modificar | Remover modelos legados do `AVAILABLE_MODELS` e corrigir nomenclaturas |
| `frontend/src/components/AddCardModal/AddCardModal.tsx` | Modificar | Atualizar `MODEL_CARDS` com nomenclaturas corretas |
| `frontend/src/constants/pricing.ts` | Modificar | Atualizar chaves dos preços com nomenclaturas corretas |
| `backend/src/schemas/card.py` | Modificar | Atualizar `ModelType` Literal com nomenclaturas corretas |
| `backend/src/config/pricing.py` | Modificar | Atualizar chaves do `MODEL_PRICING` |
| `backend/src/agent_chat.py` | Modificar | Atualizar `model_mapping` e detecção de modelos Gemini |
| `backend/src/gemini_agent.py` | Modificar | Atualizar mapeamento de modelos Gemini |
| `backend/migrations/003_update_model_nomenclature.sql` | Criar | Migration para atualizar nomenclaturas no banco de dados |

### Detalhes Técnicos

#### 1. Frontend - Tipo ModelType (`frontend/src/types/index.ts`)

```typescript
export type ModelType =
  | 'opus-4.5'
  | 'sonnet-4.5'
  | 'haiku-4.5'
  | 'gemini-3.0-pro'     // Corrigido de gemini-3-pro
  | 'gemini-3.0-flash';   // Corrigido de gemini-3-flash
```

#### 2. Frontend - ModelSelector (`frontend/src/components/Chat/ModelSelector.tsx`)

```typescript
const AVAILABLE_MODELS: AIModel[] = [
  {
    id: 'opus-4.5',
    name: 'Opus 4.5',
    provider: 'anthropic',
    contextLength: 200000,
    badge: 'Most Capable',
    category: 'claude'
  },
  {
    id: 'sonnet-4.5',
    name: 'Sonnet 4.5',
    provider: 'anthropic',
    contextLength: 200000,
    badge: 'Best Value',
    category: 'claude'
  },
  {
    id: 'haiku-4.5',
    name: 'Haiku 4.5',
    provider: 'anthropic',
    contextLength: 200000,
    category: 'claude'
  },
  {
    id: 'gemini-3.0-pro',  // Corrigido
    name: 'Gemini 3.0 Pro',
    provider: 'google',
    contextLength: 1000000,
    badge: 'Long Context',
    category: 'gemini'
  },
  {
    id: 'gemini-3.0-flash',  // Corrigido
    name: 'Gemini 3.0 Flash',
    provider: 'google',
    contextLength: 1000000,
    category: 'gemini'
  }
  // Removidos: claude-3-sonnet, claude-3-opus, gpt-4-turbo
];
```

#### 3. Frontend - AddCardModal (`frontend/src/components/AddCardModal/AddCardModal.tsx`)

```typescript
const MODEL_CARDS = [
  {
    id: 'opus-4.5' as ModelType,
    name: 'Opus 4.5',
    description: 'Most capable for complex tasks'
  },
  {
    id: 'sonnet-4.5' as ModelType,
    name: 'Sonnet 4.5',
    description: 'Best balance of speed and capability'
  },
  {
    id: 'haiku-4.5' as ModelType,
    name: 'Haiku 4.5',
    description: 'Fast responses for simple tasks'
  },
  {
    id: 'gemini-3.0-pro' as ModelType,  // Corrigido
    name: 'Gemini 3.0 Pro',
    description: 'Long context window'
  },
  {
    id: 'gemini-3.0-flash' as ModelType,  // Corrigido
    name: 'Gemini 3.0 Flash',
    description: 'Ultra-fast responses'
  }
];
```

#### 4. Backend - Schema de Validação (`backend/src/schemas/card.py`)

```python
from typing import Literal

ModelType = Literal[
    "opus-4.5",
    "sonnet-4.5",
    "haiku-4.5",
    "gemini-3.0-pro",    # Corrigido de gemini-3-pro
    "gemini-3.0-flash"   # Corrigido de gemini-3-flash
]
```

#### 5. Backend - Mapeamento de Modelos (`backend/src/agent_chat.py`)

```python
# Linha ~107 - Atualizar detecção de modelos Gemini
if model.startswith("gemini-3.0"):  # Atualizado para nova nomenclatura
    async for chunk in self._stream_response_gemini(messages, model, system_prompt):
        yield chunk

# Linha ~129 - Atualizar model_mapping
model_mapping = {
    # Claude 4.5 models - únicos permitidos
    "opus-4.5": "claude-opus-4-5",
    "sonnet-4.5": "claude-sonnet-4-5",
    "haiku-4.5": "claude-haiku-4-5",
    # Remover todos os modelos legados claude-3 e claude-3.5
}

# Para Gemini, o mapeamento será feito em gemini_agent.py
```

#### 6. Backend - Gemini Agent (`backend/src/gemini_agent.py`)

```python
# Atualizar mapeamento de modelos Gemini
def _get_gemini_model_name(self, model: str) -> str:
    """Map frontend model names to Gemini CLI model names."""
    model_map = {
        "gemini-3.0-pro": "gemini-3-pro-preview",
        "gemini-3.0-flash": "gemini-3-flash-preview"
    }
    return model_map.get(model, "gemini-3-pro-preview")
```

#### 7. Configuração de Preços

**Frontend** (`frontend/src/constants/pricing.ts`):
```typescript
export const MODEL_PRICING: Record<string, ModelPricing> = {
  'opus-4.5': { inputPricePerMillion: 15.00, outputPricePerMillion: 75.00 },
  'sonnet-4.5': { inputPricePerMillion: 3.00, outputPricePerMillion: 15.00 },
  'haiku-4.5': { inputPricePerMillion: 0.25, outputPricePerMillion: 1.25 },
  'gemini-3.0-pro': { inputPricePerMillion: 1.25, outputPricePerMillion: 5.00 },
  'gemini-3.0-flash': { inputPricePerMillion: 0.075, outputPricePerMillion: 0.30 },
};
```

**Backend** (`backend/src/config/pricing.py`):
```python
MODEL_PRICING: Dict[str, Tuple[Decimal, Decimal]] = {
    "opus-4.5": (Decimal("15.00"), Decimal("75.00")),
    "sonnet-4.5": (Decimal("3.00"), Decimal("15.00")),
    "haiku-4.5": (Decimal("0.25"), Decimal("1.25")),
    "gemini-3.0-pro": (Decimal("1.25"), Decimal("5.00")),
    "gemini-3.0-flash": (Decimal("0.075"), Decimal("0.30")),
}
```

#### 8. Migration do Banco de Dados

```sql
-- backend/migrations/003_update_model_nomenclature.sql
-- Atualizar nomenclaturas de modelos Gemini existentes

UPDATE cards
SET model_plan = 'gemini-3.0-pro'
WHERE model_plan = 'gemini-3-pro';

UPDATE cards
SET model_implement = 'gemini-3.0-pro'
WHERE model_implement = 'gemini-3-pro';

UPDATE cards
SET model_test = 'gemini-3.0-pro'
WHERE model_test = 'gemini-3-pro';

UPDATE cards
SET model_review = 'gemini-3.0-pro'
WHERE model_review = 'gemini-3-pro';

UPDATE cards
SET model_plan = 'gemini-3.0-flash'
WHERE model_plan = 'gemini-3-flash';

UPDATE cards
SET model_implement = 'gemini-3.0-flash'
WHERE model_implement = 'gemini-3-flash';

UPDATE cards
SET model_test = 'gemini-3.0-flash'
WHERE model_test = 'gemini-3-flash';

UPDATE cards
SET model_review = 'gemini-3.0-flash'
WHERE model_review = 'gemini-3-flash';
```

---

## 4. Testes

### Unitários
- [ ] Teste de validação do tipo `ModelType` no frontend
- [ ] Teste de validação do schema Pydantic no backend
- [ ] Teste de mapeamento de modelos para APIs externas
- [ ] Teste de detecção de modelos Gemini com nova nomenclatura

### Integração
- [ ] Teste de criação de card com cada modelo permitido
- [ ] Teste de rejeição de modelos não permitidos (ex: claude-3-opus)
- [ ] Teste de seleção de modelo no chat
- [ ] Teste de execução de comandos com modelos Gemini renomeados
- [ ] Verificar que cards existentes com nomenclaturas antigas continuam funcionando após migration

### Testes Manuais
- [ ] Criar novo card e verificar que apenas 5 modelos aparecem no seletor
- [ ] Verificar que o chat mostra apenas os 5 modelos permitidos
- [ ] Testar execução de comando /plan com modelo gemini-3.0-pro
- [ ] Verificar que preços são calculados corretamente com novas nomenclaturas

---

## 5. Considerações

### Riscos
- **Cards existentes com modelos antigos**: Mitigado pela migration SQL que atualiza nomenclaturas
- **Cache do frontend**: Usuários podem precisar fazer hard refresh (Ctrl+F5) para ver mudanças
- **Integração com APIs externas**: Mapeamento atualizado garante compatibilidade

### Dependências
- Migration deve ser executada antes do deploy do novo código
- Frontend e backend devem ser deployados juntos para evitar inconsistências

### Validação Adicional
- Adicionar validação explícita no frontend antes de enviar requests
- Log de warning quando modelo inválido for detectado
- Monitorar erros de validação após deploy