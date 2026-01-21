---
description: Cria planos de implementação detalhados para features, bugs ou refatorações. Use antes de implementar tarefas complexas.
argument-hint: [descrição da tarefa]
allowed-tools: Read, Glob, Grep, Write, Task
model: opus
---

**Nota:** O modelo Claude usado para este comando pode ser configurado por card na UI. O padrão é Opus 4.5.

# Plan

Crie um plano de implementação detalhado com base na solicitação do usuário: $ARGUMENTS

Salve o planejamento em `specs/<nome_descritivo>.md`

## Instruções

1. Se `$ARGUMENTS` estiver vazio, pergunte ao usuário o que deseja implementar
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

Descreva a abordagem técnica, incluindo snippets de código quando relevante:

```typescript
// Exemplo de implementação
```

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
