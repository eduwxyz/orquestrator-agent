---
description: Implementa um plano de specs/*.md gerado pelo comando /plan. Lê o plano, implementa cada item e marca como concluído.
argument-hint: [caminho/para/spec.md]
model: opus
---

**Nota:** O modelo Claude usado para este comando pode ser configurado por card na UI. O padrão é Opus 4.5.

# Implement

Implemente o plano especificado em: $ARGUMENTS

## Instruções

1. Se `$ARGUMENTS` estiver vazio, liste os arquivos disponíveis em `specs/` e pergunte qual implementar
2. Leia o arquivo de plano especificado
3. Analise todas as seções do plano
4. Implemente cada item na ordem definida
5. Atualize o arquivo de plano marcando checkboxes conforme conclui cada item

## Workflow de Implementação

### Fase 1: Análise do Plano

1. Leia o arquivo de plano completo
2. Extraia a lista de arquivos a serem modificados/criados da tabela
3. Extraia os objetivos e escopo
4. Extraia os detalhes técnicos e snippets de código
5. Crie uma lista de tarefas baseada nos itens do plano

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
4. Se houver testes de integração, execute-os também

### Fase 4: Finalização

1. Revise se todos os objetivos foram atendidos
2. Marque todos os checkboxes restantes
3. Apresente um resumo do que foi implementado

## Regras

- **Sempre** leia o arquivo de plano antes de implementar
- **Sempre** siga a ordem definida no plano
- **Sempre** atualize os checkboxes no arquivo de plano conforme progride
- **Nunca** pule etapas definidas no plano
- **Mantenha** consistência com padrões existentes na codebase
- Se encontrar ambiguidades no plano, pergunte antes de prosseguir

## Formato de Atualização de Checkboxes

Ao completar um objetivo:
```diff
- - [ ] Objetivo 1
+ - [x] Objetivo 1
```

Ao completar um teste:
```diff
- - [ ] Teste 1
+ - [x] Teste 1
```

## Exemplo de Uso

```
/implement specs/feature-auth.md
```

O comando irá:
1. Ler `specs/feature-auth.md`
2. Criar/modificar os arquivos listados
3. Implementar a lógica descrita
4. Executar e validar os testes
5. Atualizar o arquivo de plano com os checkboxes marcados
6. Retorne para o usuário um resumo do que foi feito
