# Plano de Implementação: Corrigir Requests do Chat para Usar Claude Code

## 1. Resumo

O sistema de chat atualmente usa o Claude Agent SDK com o comando `/question`, mas de forma incorreta. Precisamos alinhar a implementação do chat para usar as mesmas práticas dos comandos `/plan`, `/implement`, garantindo que as requests sejam feitas através do Claude Code de forma consistente com o resto do sistema.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Remover o uso do comando `/question` no chat que está limitando as capacidades
- [x] Implementar chamadas diretas ao Claude Code sem comandos pré-definidos
- [x] Manter o streaming em tempo real via WebSocket
- [x] Preservar o histórico de conversação
- [x] Garantir que o modelo selecionado seja respeitado corretamente

### Fora do Escopo
- Mudanças na interface do usuário
- Alteração no sistema de WebSocket
- Modificações nos comandos `/plan`, `/implement`, etc.
- Persistência do histórico de chat em banco de dados

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/agent_chat.py` | Modificar | Remover uso de `/question`, implementar chamada direta ao Claude |
| `backend/src/services/chat_service.py` | Modificar | Ajustar para usar novo método do agent_chat |
| `backend/src/routes/chat.py` | Modificar | Adicionar suporte para configurações adicionais se necessário |

### Detalhes Técnicos

#### 1. Modificar `backend/src/agent_chat.py`

Atualmente o arquivo está usando o comando `/question` que limita as capacidades. Vamos refatorar para usar o Claude Agent SDK diretamente:

```python
class ClaudeAgentChat:
    async def stream_response(
        self,
        messages: list[dict],
        model: str = "claude-3.5-sonnet",
        system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from Claude using Claude Agent SDK directly
        without predefined commands like /question
        """
        from claude_agent_sdk import query, ClaudeAgentOptions
        from claude_agent_sdk import AssistantMessage, TextBlock, ResultMessage

        # Map model names to SDK format
        model_mapping = {
            "claude-3.5-opus": "opus",
            "claude-3.5-sonnet": "sonnet",
            "claude-3.5-haiku": "haiku",
            "claude-3-sonnet": "sonnet",
            "claude-3-opus": "opus",
            "opus-4.5": "opus",
        }
        agent_model = model_mapping.get(model, "sonnet")

        # Build conversation context
        # Instead of using /question command, send direct prompt with full context
        full_prompt = ""

        # Add system prompt if provided
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"

        # Add conversation history
        if len(messages) > 1:
            full_prompt += "Previous conversation:\n"
            for msg in messages[:-1]:
                role = "User" if msg["role"] == "user" else "Assistant"
                full_prompt += f"{role}: {msg['content']}\n"
            full_prompt += "\n"

        # Add current user message
        user_message = messages[-1]["content"]
        full_prompt += f"User: {user_message}\n\nAssistant:"

        # Configure Claude Agent SDK Options - same as /plan but with appropriate tools
        options = ClaudeAgentOptions(
            cwd=os.getcwd(),  # Use project root
            setting_sources=["user", "project"],
            allowed_tools=[
                "Read",      # Read files
                "Bash",      # Execute commands
                "Glob",      # Search files
                "Grep",      # Search content
                "WebSearch", # Web search capability
                "WebFetch",  # Fetch web content
                "Task",      # Launch agents for complex tasks
                "Skill",     # Use skills
            ],
            permission_mode="bypassPermissions",  # Auto-approve for chat
            model=agent_model,
        )

        # Execute query directly without command prefix
        async for message in query(prompt=full_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        # Stream text content
                        yield block.text
            elif isinstance(message, ResultMessage):
                if hasattr(message, "result") and message.result:
                    yield message.result
```

#### 2. Atualizar `backend/src/services/chat_service.py`

Garantir que o serviço está passando os parâmetros corretos:

```python
class ChatService:
    async def send_message(
        self,
        session_id: str,
        message: str,
        model: str = "claude-3-sonnet"
    ) -> AsyncGenerator[dict, None]:
        """Send message to Claude and stream response"""

        # Store user message
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "model": model,
        }
        self.sessions[session_id].append(user_message)

        # Prepare messages for Claude
        claude_messages = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.sessions[session_id]
        ]

        # Get system prompt if configured
        system_prompt = self.get_system_prompt()  # Method to get custom prompt if needed

        # Stream response from Claude Agent
        assistant_content = ""
        assistant_message_id = str(uuid.uuid4())

        try:
            async for chunk in self.claude_agent.stream_response(
                messages=claude_messages,
                model=model,
                system_prompt=system_prompt
            ):
                assistant_content += chunk
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "messageId": assistant_message_id,
                }

            # Store complete assistant message
            assistant_message = {
                "role": "assistant",
                "content": assistant_content,
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "messageId": assistant_message_id,
            }
            self.sessions[session_id].append(assistant_message)

            # Send completion signal
            yield {
                "type": "end",
                "messageId": assistant_message_id,
            }

        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "messageId": assistant_message_id,
            }

    def get_system_prompt(self) -> str | None:
        """Get system prompt for chat context"""
        # Could be loaded from config or database
        return """You are Claude, an AI assistant created by Anthropic.
        You are integrated into a development environment where you can help with coding tasks.
        Be helpful, accurate, and concise in your responses."""
```

#### 3. Validar modelos em `backend/src/routes/chat.py`

Adicionar novos modelos se necessário:

```python
# Lista atualizada de modelos permitidos
ALLOWED_MODELS = [
    "claude-3.5-opus",
    "claude-3.5-sonnet",
    "claude-3.5-haiku",
    "claude-3-sonnet",
    "claude-3-opus",
    "opus-4.5",  # Adicionar suporte para opus-4.5
]

@router.websocket("/ws/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for chat"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Validate message type
            message_type = message_data.get("type")
            if message_type != "message":
                continue

            # Extract message details
            message_content = message_data.get("content")
            message_model = message_data.get("model", "claude-3.5-sonnet")

            # Validate model
            if message_model not in ALLOWED_MODELS:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": f"Invalid model: {message_model}"
                }))
                continue

            # Process message
            async for chunk in chat_service.send_message(
                session_id=session_id,
                message=message_content,
                model=message_model,
            ):
                await websocket.send_text(json.dumps(chunk))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1000)
```

---

## 4. Testes

### Unitários
- [x] Testar mapeamento de modelos no `agent_chat.py`
- [x] Testar construção de prompt com histórico de conversação
- [x] Testar streaming de respostas

### Integração
- [x] Testar chat com diferentes modelos (opus, sonnet, haiku)
- [x] Testar manutenção de contexto em conversas longas
- [x] Testar uso de ferramentas (Read, Bash, etc) no chat
- [x] Testar tratamento de erros e reconexão WebSocket

### Testes Manuais
- [x] Enviar mensagem simples e verificar resposta
- [x] Trocar modelo durante conversa
- [x] Pedir para ler um arquivo específico
- [x] Pedir para executar comando bash
- [x] Verificar que o streaming funciona corretamente

---

## 5. Considerações

### Riscos
- **Performance:** Remover `/question` pode aumentar latência inicial
  - **Mitigação:** Otimizar construção de prompt e cache de configurações

- **Ferramentas:** Dar mais permissões ao chat pode ser perigoso
  - **Mitigação:** Manter `bypassPermissions` mas com tools limitadas

### Melhorias Futuras
- Implementar persistência do histórico de chat em banco de dados
- Adicionar configuração de system prompt personalizado por usuário
- Implementar rate limiting para prevenir abuso
- Cache de respostas para perguntas frequentes

### Dependências
- Nenhuma nova dependência necessária
- Usa `claude-agent-sdk` já instalado
- Compatível com infraestrutura WebSocket existente