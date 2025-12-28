# Adicionar Botão "Create PR" em Cards na Coluna Done

## 1. Resumo

Adicionar um botão visual "Create PR" nos cards quando eles estiverem na coluna "Done". O botão será apenas visual neste momento (não terá funcionalidade), servindo como preparação para uma feature futura de criação automática de Pull Requests. O objetivo é melhorar a UI indicando ao usuário que há uma ação disponível quando a tarefa está finalizada.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar botão "Create PR" visível apenas em cards na coluna "Done"
- [x] Manter consistência visual com o botão "Run" existente no Backlog
- [x] Botão deve aparecer no hover do card (como o botão Run)
- [x] Botão não deve executar nenhuma ação (onClick vazio ou apenas preventDefault)

### Fora do Escopo
- Implementação da funcionalidade de criação de PR
- Integração com GitHub API
- Qualquer lógica de backend

---

## 3. Implementação

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Card/Card.tsx` | Modificar | Adicionar renderização condicional do botão Create PR |
| `frontend/src/components/Card/Card.module.css` | Modificar | Adicionar estilos para o botão Create PR |

### Detalhes Técnicos

**Card.tsx - Adicionar botão Create PR**

O botão deve ser renderizado condicionalmente quando `card.columnId === 'done'`, similar ao botão Run que aparece em `card.columnId === 'backlog'`.

Localização: após o bloco do botão Run (linha 91-111), adicionar:

```typescript
{card.columnId === 'done' && (
  <button
    className={styles.createPrButton}
    onClick={(e) => {
      e.stopPropagation();
      // Placeholder: funcionalidade será implementada futuramente
    }}
    aria-label="Create Pull Request"
    title="Criar Pull Request para esta feature"
  >
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="currentColor"
    >
      <path d="M13 3a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm0-1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM3 13a1 1 0 1 1 0 2 1 1 0 0 1 0-2zm0-1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0-10a1 1 0 1 1 0 2 1 1 0 0 1 0-2zM3 1a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm9.5 4.5V8h-1V5.5h1zM4 4.5v7h-1v-7h1zm8.5 8V10h1v2.5a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 0-1.5 1.5v.5h-1v-.5A2.5 2.5 0 0 1 5 13h7a.5.5 0 0 0 .5-.5z"/>
    </svg>
    Create PR
  </button>
)}
```

**Observações:**
- O SVG usado é o ícone de "git-pull-request" do conjunto de ícones Octicons (GitHub)
- O `e.stopPropagation()` evita que o click abra o modal de logs
- O botão segue a mesma estrutura do botão Run para manter consistência

**Card.module.css - Estilos do botão Create PR**

Adicionar após os estilos do `.runButton` (linha 254-289):

```css
/* Create PR Button Styles */
.createPrButton {
  position: absolute;
  top: 8px;
  right: 40px;
  padding: 4px 8px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  z-index: 10;
  opacity: 0;
  transform: scale(0.8);
}

.card:hover .createPrButton {
  opacity: 1;
  transform: scale(1);
}

.createPrButton:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(16, 185, 129, 0.3);
}

.createPrButton svg {
  width: 12px;
  height: 12px;
}
```

**Observações:**
- Gradiente verde (emerald) para diferenciar do botão Run (roxo)
- Mesma posição e comportamento de hover/transição do botão Run
- O verde representa "pronto para merge/PR"

---

## 4. Testes

### Testes Manuais
- [ ] Verificar que o botão Create PR aparece apenas em cards na coluna "Done"
- [ ] Verificar que o botão não aparece em outras colunas (Backlog, Plan, In Progress, Test, Review)
- [ ] Verificar que o botão aparece no hover do card
- [ ] Verificar que o click no botão não quebra a aplicação
- [ ] Verificar que o click no botão não abre o modal de logs
- [ ] Verificar alinhamento visual com o botão de remover (X)
- [ ] Verificar responsividade do botão em diferentes tamanhos de tela

### Casos de Teste
1. Mover um card para Done e verificar aparecimento do botão
2. Mover um card de Done para outra coluna e verificar desaparecimento do botão
3. Hover no card em Done deve mostrar ambos os botões (Create PR e X)

---

## 5. Considerações

### Design
- **Cor escolhida:** Verde (emerald) foi escolhido para representar "conclusão" e "pronto para PR", diferenciando-se do roxo do botão Run
- **Posicionamento:** Mesmo posicionamento do botão Run (top: 8px, right: 40px) para manter consistência
- **Ícone:** Ícone de Git Pull Request para deixar claro o propósito do botão

### Futuras Implementações
- **Funcionalidade:** O botão está preparado para receber a função de criar PR futuramente
- **Props:** Pode ser necessário adicionar uma prop `onCreatePR` no componente Card, similar ao `onRunWorkflow`
- **Estados:** Considerar adicionar estados de loading/sucesso/erro quando a funcionalidade for implementada

### Riscos
- **Nenhum risco técnico:** Mudança puramente visual e isolada
- **Expectativa do usuário:** Usuário pode tentar clicar e esperar ação. Considerar adicionar um toast/notificação informando "Em breve" na primeira implementação
