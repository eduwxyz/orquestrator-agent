# Spec: Melhoria da UI do Modal de Logs

## Objetivo
Melhorar a experiência de visualização de logs com duas correções principais:
1. Aumentar o tamanho do modal sem sobrepor 100% do kanban
2. Exibir logs em tempo real durante a execução

## Análise do Problema

### Problema 1: Tamanho do Modal
- Modal atual: `max-width: 900px`, `max-height: 85vh`
- Na screenshot, o modal aparece muito pequeno, com texto truncado
- O modal está centralizado, cobrindo a área do kanban

### Problema 2: Logs só aparecem quando card finaliza
- O frontend usa `fetch` com `await` que só retorna quando a execução termina
- O backend já salva logs em tempo real no dicionário `executions` em memória
- O endpoint `/api/logs/{card_id}` existe mas não está sendo usado durante execução
- Solução: usar polling para buscar logs durante a execução

## Implementação

### Checklist

- [x] **1. Frontend - Ajustar CSS do Modal** (`LogsModal.module.css`)
  - Aumentar largura máxima para ~55% da tela (ajuste responsivo)
  - Posicionar modal à direita para não cobrir todo o kanban
  - Aumentar altura máxima (100% da tela)
  - Melhorar layout dos logs para texto longo (layout vertical)

- [x] **2. Frontend - Implementar polling de logs** (`useAgentExecution.ts`)
  - Criar função para buscar logs do endpoint `/api/logs/{card_id}`
  - Iniciar polling quando execução começa (status = 'running')
  - Atualizar logs no estado a cada 1.5 segundos
  - Parar polling quando execução termina

- [x] **3. Frontend - Ajustar LogsModal.tsx**
  - Garantir que área de logs tenha scroll adequado
  - Auto-scroll para novos logs
  - Removido agrupamento de logs para simplificar visualização

## Arquivos a Modificar

1. `frontend/src/components/LogsModal/LogsModal.module.css`
2. `frontend/src/hooks/useAgentExecution.ts`
3. `frontend/src/components/LogsModal/LogsModal.tsx` (se necessário)

## Testes

- [x] Verificar que arquivos modificados não têm erros de TypeScript
- [ ] Verificar que modal abre com tamanho maior (teste manual)
- [ ] Verificar que modal não cobre 100% da tela - kanban visível (teste manual)
- [ ] Verificar que logs aparecem em tempo real durante execução (teste manual)
- [ ] Verificar auto-scroll para novos logs (teste manual)

**Nota:** Testes manuais requerem execução do frontend e backend.

## Revisão

### Mudanças Realizadas

1. **LogsModal.module.css**
   - Modal agora posicionado à direita (55% da largura da tela)
   - Altura total da tela disponível
   - Animação de slide-in da direita
   - Layout dos logs em formato vertical para melhor legibilidade

2. **useAgentExecution.ts**
   - Implementado sistema de polling com intervalo de 1.5s
   - Polling inicia automaticamente quando execução começa
   - Polling para automaticamente quando execução termina
   - Cleanup adequado no unmount do componente
   - Logs são atualizados incrementalmente

3. **LogsModal.tsx**
   - Removido agrupamento de logs por tipo (simplificado)
   - Cada log agora tem header com timestamp + tipo
   - Melhor visualização de logs longos

### Pontos Positivos
- Polling usa endpoint existente `/api/logs/{cardId}` sem mudanças no backend
- Cleanup adequado de intervals
- Performance otimizada (só atualiza estado se há novos logs)

### Testes Manuais Necessários
- Abrir modal de logs durante uma execução e verificar atualização em tempo real
- Verificar que modal não cobre 100% da tela
