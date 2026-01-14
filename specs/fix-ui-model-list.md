# Corrigir Lista de Modelos de IA na Interface

## 1. Resumo

Corrigir a lista de modelos de IA que aparecem no seletor do chat, atualizando de modelos Claude 3.5 e Gemini 2.0 (nomenclatura antiga) para os novos modelos Opus 4.5, Sonnet 4.5, Haiku 4.5, Gemini 3 Pro e Gemini 3 Flash. O problema está em inconsistências entre os IDs usados no ModelSelector e as definições de tipos/constantes do sistema.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Atualizar lista de modelos no componente ModelSelector para usar IDs corretos
- [x] Corrigir configuração de pricing no backend para usar os mesmos IDs
- [x] Ajustar valor padrão do schema SendMessageRequest no backend
- [x] Garantir consistência entre frontend e backend na nomenclatura de modelos

### Fora do Escopo
- Adicionar novos modelos além dos especificados
- Alterar preços dos modelos existentes
- Modificar a lógica de seleção ou interface visual do seletor

---

## 3. Implementação

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Chat/ModelSelector.tsx` | Modificar | Atualizar AVAILABLE_MODELS com IDs e labels corretos |
| `backend/src/config/pricing.py` | Modificar | Atualizar chaves do dicionário MODEL_PRICING |
| `backend/src/schemas/chat.py` | Modificar | Corrigir valor padrão do campo model em SendMessageRequest |

### Detalhes Técnicos

#### 1. ModelSelector.tsx - Atualizar lista de modelos disponíveis

Substituir o array `AVAILABLE_MODELS` (linhas 9-95) por:

```typescript
const AVAILABLE_MODELS: ModelOption[] = [
  {
    value: 'opus-4.5',
    label: 'Opus 4.5',
    provider: 'claude',
    description: 'Most capable for complex tasks',
    icon: <Brain className={styles.modelIcon} />,
    color: '#8B5CF6',
    pricing: MODEL_PRICING['opus-4.5']
  },
  {
    value: 'sonnet-4.5',
    label: 'Sonnet 4.5',
    provider: 'claude',
    description: 'Balanced performance',
    icon: <Zap className={styles.modelIcon} />,
    color: '#3B82F6',
    pricing: MODEL_PRICING['sonnet-4.5']
  },
  {
    value: 'haiku-4.5',
    label: 'Haiku 4.5',
    provider: 'claude',
    description: 'Fast and efficient',
    icon: <Sparkles className={styles.modelIcon} />,
    color: '#10B981',
    pricing: MODEL_PRICING['haiku-4.5']
  },
  {
    value: 'gemini-3-pro',
    label: 'Gemini 3 Pro',
    provider: 'gemini',
    description: 'Advanced reasoning',
    icon: <Star className={styles.modelIcon} />,
    color: '#F59E0B',
    pricing: MODEL_PRICING['gemini-3-pro']
  },
  {
    value: 'gemini-3-flash',
    label: 'Gemini 3 Flash',
    provider: 'gemini',
    description: 'Lightning fast',
    icon: <Zap className={styles.modelIcon} />,
    color: '#EF4444',
    pricing: MODEL_PRICING['gemini-3-flash']
  }
];
```

#### 2. backend/src/config/pricing.py - Atualizar chaves do dicionário

Substituir o dicionário `MODEL_PRICING` (linhas 6-19) por:

```python
MODEL_PRICING = {
    # Claude 4.5 models
    "opus-4.5": (Decimal("15.00"), Decimal("75.00")),
    "sonnet-4.5": (Decimal("3.00"), Decimal("15.00")),
    "haiku-4.5": (Decimal("0.25"), Decimal("1.25")),

    # Gemini 3 models
    "gemini-3-pro": (Decimal("1.25"), Decimal("5.00")),
    "gemini-3-flash": (Decimal("0.075"), Decimal("0.30")),
}
```

#### 3. backend/src/schemas/chat.py - Corrigir valor padrão

Atualizar a linha 38 de:
```python
model: Optional[str] = 'claude-3.5-sonnet'
```

Para:
```python
model: Optional[str] = 'sonnet-4.5'
```

---

## 4. Testes

### Manuais
- [x] Abrir a página de chat e verificar se aparecem os 5 modelos corretos no dropdown
- [x] Selecionar cada modelo e enviar uma mensagem para testar funcionamento
- [x] Verificar se o modelo padrão é Sonnet 4.5 ao abrir o chat
- [x] Criar um novo card e verificar se os modelos corretos aparecem nas opções de workflow

### Validações
- [x] Verificar que os IDs no frontend correspondem aos tipos definidos em `types/index.ts`
- [x] Confirmar que o pricing é calculado corretamente com os novos IDs
- [x] Testar que o mapeamento no `agent_chat.py` funciona com os novos IDs

---

## 5. Considerações

- **Compatibilidade:** O backend mantém suporte para os IDs antigos (`claude-3.5-*`) através do mapeamento em `agent_chat.py`, garantindo retrocompatibilidade
- **Consistência:** Após essas mudanças, todos os componentes usarão a mesma nomenclatura (`opus-4.5`, `sonnet-4.5`, etc.)
- **Impacto:** Mudança é transparente para o usuário final, apenas corrige os modelos exibidos na interface