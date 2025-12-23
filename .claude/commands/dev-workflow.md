---
description: Workflow completo de desenvolvimento (plan → implement → test → review). Use para features ou bugs.
argument-hint: [descrição da feature ou bug]
---

# Dev Workflow

Execute o workflow completo de desenvolvimento para: $ARGUMENTS

## Validação

1. Se `$ARGUMENTS` estiver vazio, pergunte ao usuário o que deseja implementar antes de continuar

## Workflow

Execute as seguintes etapas **sequencialmente**, aguardando conclusão de cada uma:

### 1. Planejamento

- Execute o fluxo do comando `/plan` com: $ARGUMENTS
- Salve o plano em `specs/<nome_descritivo>.md`
- Armazene o caminho do arquivo para uso nas próximas etapas
- Prossiga automaticamente para a próxima etapa

### 2. Implementação

- Execute o fluxo do comando `/implement` com o arquivo de spec criado
- Implemente todos os itens do plano
- Atualize checkboxes no arquivo de spec
- Prossiga automaticamente para a próxima etapa

### 3. Testes

- Execute o fluxo do comando `/test-implementation` referenciando o spec
- Implemente e execute os testes definidos no plano
- Corrija falhas se necessário
- Prossiga automaticamente para a próxima etapa

### 4. Revisão

- Execute o fluxo do comando `/review` nas mudanças realizadas
- Identifique melhorias e problemas
- Sugira correções se necessário

## Finalização

Apresente resumo:
- Feature/Bug trabalhado
- Arquivos modificados/criados
- Status dos testes
- Resultado da revisão
- Próximos passos sugeridos (PR, code review, etc.)

## Regras

- Execute todas as etapas automaticamente sem interrupção
- Mantenha transparência sobre o que está sendo feito em cada etapa
- Se houver erro crítico, corrija e continue automaticamente
