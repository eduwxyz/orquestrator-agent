# Fix Chat Models and Remove Commands Usage

## 1. Resumo

Ajustar os modelos disponíveis no seletor de chat para exibir apenas Opus 4.5, Sonnet 4.5 e Haiku 4.5, garantindo o mapeamento correto para a API. Além disso, remover o uso do comando `/question` para que as mensagens sejam enviadas diretamente ao assistente sem comandos.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Remover todos os modelos antigos da UI (Claude 3.x, GPT-4)
- [x] Manter apenas Opus 4.5, Sonnet 4.5 e Haiku 4.5
- [x] Garantir mapeamento correto dos IDs dos modelos
- [x] Remover uso de `/question` no backend
- [x] Enviar mensagens diretamente sem comandos

### Fora do Escopo
- Alterações no layout do seletor
- Mudanças na funcionalidade de chat existente além das especificadas
- Alterações na interface de chat além do seletor de modelos

---

## 3. Implementação

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Chat/ModelSelector.tsx` | Modificar | Atualizar lista de modelos disponíveis |
| `frontend/src/hooks/useChat.ts` | Modificar | Ajustar modelo padrão para ID correto |
| `backend/src/agent_chat.py` | Modificar | Remover uso de /question e enviar prompt direto |

### Detalhes Técnicos

#### 1. Atualização do ModelSelector.tsx

```typescript
export const AVAILABLE_MODELS: AIModel[] = [
  {
    id: 'opus-4.5',
    name: 'Opus 4.5',
    displayName: 'Opus 4.5',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Most powerful model for complex reasoning and advanced tasks',
    performance: 'powerful',
    icon: '🧠',
    accent: 'anthropic',
    badge: 'Most Capable'
  },
  {
    id: 'sonnet-4.5',
    name: 'Sonnet 4.5',
    displayName: 'Sonnet 4.5',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Balanced performance and speed for most tasks',
    performance: 'balanced',
    icon: '⚡',
    accent: 'anthropic',
    badge: 'Best Value'
  },
  {
    id: 'haiku-4.5',
    name: 'Haiku 4.5',
    displayName: 'Haiku 4.5',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Fast responses for simple tasks and quick interactions',
    performance: 'fastest',
    icon: '🚀',
    accent: 'anthropic'
  }
];
```

#### 2. Atualização do useChat.ts

```typescript
// Mudar modelo padrão para sonnet-4.5
const [state, setState] = useState<ChatState>({
  // ...
  selectedModel: 'sonnet-4.5',
  // ...
});
```

#### 3. Modificação do agent_chat.py

Remover o uso de `/question` e enviar as mensagens diretamente:

```python
async def stream_response(
    self,
    messages: list[dict],
    model: str = "sonnet-4.5",
    system_prompt: str | None = None
) -> AsyncGenerator[str, None]:
    # ... código existente ...

    # Em vez de usar /question, construir prompt direto
    # Obter última mensagem do usuário
    user_message = None
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_message = msg["content"]
            break

    # Construir prompt direto sem comando
    prompt = user_message

    # Adicionar contexto das mensagens anteriores se houver
    if len(messages) > 1:
        context = "\n\nPrevious conversation:\n"
        for msg in messages[:-1]:
            role = "User" if msg["role"] == "user" else "Assistant"
            context += f"{role}: {msg['content']}\n"
        prompt = context + "\n\nCurrent question:\n" + user_message

    # Mapear modelos para valores esperados pelo SDK
    model_mapping = {
        "opus-4.5": "opus",
        "sonnet-4.5": "sonnet",
        "haiku-4.5": "haiku",
    }
    agent_model = model_mapping.get(model, "sonnet")

    # Configurar opções sem restrições de comandos
    options = ClaudeAgentOptions(
        cwd=cwd,
        setting_sources=["user", "project"],
        allowed_tools=["Read", "Bash", "Glob", "Grep", "Skill"],
        permission_mode="bypassPermissions",
        model=agent_model,
    )

    # Enviar diretamente ao agente
    async for message in query(prompt=prompt, options=options):
        # processar resposta...
```

---

## 4. Testes

### Unitários
- [x] Verificar que apenas 3 modelos aparecem no seletor
- [x] Confirmar que os IDs são opus-4.5, sonnet-4.5 e haiku-4.5
- [x] Validar mapeamento correto no backend

### Integração
- [x] Testar envio de mensagem com cada modelo
- [x] Verificar que mensagens são enviadas sem comando /question
- [x] Confirmar que o contexto é mantido corretamente

---

## 5. Considerações

- **Riscos:** Mudança pode afetar sessões de chat existentes se houver persistência. Mitigar testando em ambiente de desenvolvimento primeiro.
- **Dependências:** SDK do Claude Agent precisa aceitar queries diretas sem comandos específicos