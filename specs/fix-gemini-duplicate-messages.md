## 1. Resumo

Corrigir o bug de duplicação de mensagens ao utilizar o modelo Gemini no chat. O problema ocorre devido ao processamento duplo de mensagens no handler do Claude Agent SDK, que está fazendo yield tanto de TextBlocks quanto de ResultMessages, causando conteúdo duplicado no frontend.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Eliminar duplicação de mensagens no chat ao usar Gemini
- [x] Manter o streaming funcionando corretamente
- [x] Garantir que a correção não afete o chat com Claude
- [x] Preservar a funcionalidade de streaming em tempo real

### Fora do Escopo
- Refatoração completa do sistema de chat
- Mudanças na UI/UX do chat
- Otimizações de performance não relacionadas ao bug

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/agent_chat.py` | Modificar | Corrigir o yield duplo no método stream_response() |
| `backend/src/services/chat_service.py` | Revisar | Verificar se há processamento adicional desnecessário |

### Detalhes Técnicos

#### **Problema Principal: agent_chat.py (linhas 183-191)**

O código atual está fazendo yield de dois tipos de mensagens que podem conter conteúdo duplicado:

```python
# CÓDIGO ATUAL (COM BUG)
async for message in query(prompt=full_prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                # Stream text content
                yield block.text  # ← YIELD #1
    elif isinstance(message, ResultMessage):
        if hasattr(message, "result") and message.result:
            yield message.result   # ← YIELD #2 (DUPLICAÇÃO!)
```

#### **Solução Proposta**

Remover o yield do ResultMessage, pois o conteúdo já foi enviado através dos TextBlocks:

```python
# CÓDIGO CORRIGIDO
async for message in query(prompt=full_prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                # Stream text content
                yield block.text  # ← Mantém apenas este yield
    elif isinstance(message, ResultMessage):
        # Log para debug, mas NÃO faz yield do resultado
        # pois o conteúdo já foi enviado através dos TextBlocks
        if hasattr(message, "result") and message.result:
            print(f"[ClaudeAgentChat] ResultMessage received (not yielding): {len(message.result)} chars")
            # Opcional: Salvar em log ou metrics, mas não enviar ao cliente
```

#### **Alternativa (se necessário distinguir tipos)**

Se for necessário processar ResultMessage de forma diferente, podemos adicionar um tipo ao yield:

```python
# ALTERNATIVA - Com tipagem de mensagens
async for message in query(prompt=full_prompt, options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                # Stream text content chunks
                yield {
                    "type": "text_chunk",
                    "content": block.text
                }
    elif isinstance(message, ResultMessage):
        # Send completion signal only, sem conteúdo duplicado
        if hasattr(message, "result") and message.result:
            yield {
                "type": "completion",
                "content": None  # Não envia conteúdo, apenas sinaliza fim
            }
```

E então ajustar o chat_service.py para processar apenas chunks de texto:

```python
# Em chat_service.py
async for chunk in self.claude_agent.stream_response(...):
    if isinstance(chunk, dict) and chunk.get("type") == "text_chunk":
        assistant_content += chunk["content"]
        yield {
            "type": "chunk",
            "content": chunk["content"],
            "messageId": assistant_message_id,
        }
    elif isinstance(chunk, str):
        # Backward compatibility
        assistant_content += chunk
        yield {
            "type": "chunk",
            "content": chunk,
            "messageId": assistant_message_id,
        }
```

---

## 4. Testes

### Testes Manuais
**⚠️ AÇÃO NECESSÁRIA: Os testes abaixo devem ser realizados pelo usuário após iniciar o backend**

- [ ] Enviar mensagem usando modelo Gemini e verificar se não há duplicação
- [ ] Enviar mensagem usando modelo Claude e verificar se continua funcionando
- [ ] Testar streaming com mensagens longas no Gemini
- [ ] Testar streaming com mensagens longas no Claude
- [ ] Verificar se o histórico de chat está sendo salvo corretamente

### Cenários de Teste

1. **Teste de Duplicação com Gemini**:
   - Enviar: "O que é mandado?" (como na imagem)
   - Esperado: Resposta única sem linhas duplicadas

2. **Teste de Streaming**:
   - Enviar: "Escreva um texto longo sobre IA"
   - Esperado: Texto aparece progressivamente sem duplicação

3. **Teste de Alternância de Modelos**:
   - Enviar mensagem com Claude
   - Trocar para Gemini e enviar mensagem
   - Trocar de volta para Claude
   - Esperado: Todas as respostas sem duplicação

### Validação de Logs
- [ ] Verificar logs do backend para confirmar que ResultMessage não está sendo yielded
- [ ] Confirmar que não há erros ou warnings após a correção

---

## 5. Considerações

### Riscos
- **Risco Baixo**: A mudança é isolada e afeta apenas o processamento de mensagens do Claude Agent SDK
- **Mitigação**: Manter logs detalhados durante os primeiros dias após deploy

### Rollback
- Se houver problemas, reverter o commit específico em agent_chat.py
- O código atual (com duplicação) está funcionando, apenas com o bug visual

### Monitoramento Pós-Deploy
- Observar logs por 24h após deploy
- Coletar feedback de usuários sobre a experiência do chat
- Verificar métricas de latência do streaming