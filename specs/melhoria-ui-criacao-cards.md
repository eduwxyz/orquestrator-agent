# Melhoria da UI de Criação de Cards - Modal Centralizado

## 1. Resumo

Transformar a interface de criação de cards de um formulário inline limitado à coluna backlog para um modal centralizado em tela cheia com design moderno e melhorado. O objetivo é proporcionar uma experiência mais imersiva e profissional ao criar novos cards no sistema kanban.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Converter o formulário inline de criação em um modal centralizado
- [x] Melhorar o design visual utilizando a skill frontend-design
- [x] Implementar overlay com backdrop blur para foco na criação
- [x] Redesenhar a seleção de modelos com cards visuais
- [x] Adicionar animações suaves de entrada/saída
- [x] Manter funcionalidade de upload de imagens com preview melhorado
- [x] Criar experiência mais profissional e polida

### Fora do Escopo
- Alteração da lógica de backend
- Modificação do fluxo de drag-and-drop
- Mudanças nas outras colunas do kanban

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/AddCardModal/AddCardModal.tsx` | Criar | Novo componente de modal centralizado |
| `frontend/src/components/AddCardModal/AddCardModal.module.css` | Criar | Estilos do modal com design moderno |
| `frontend/src/components/AddCard/AddCard.tsx` | Modificar | Simplificar para apenas botão que abre modal |
| `frontend/src/components/Column/Column.tsx` | Modificar | Integrar novo modal |
| `frontend/src/App.tsx` | Modificar | Adicionar portal root para modal |

### Detalhes Técnicos

#### 1. Estrutura do Modal
```typescript
// AddCardModal.tsx
interface AddCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (cardData: CardFormData) => Promise<void>;
}

export function AddCardModal({ isOpen, onClose, onSubmit }: AddCardModalProps) {
  // Portal para renderizar fora do DOM principal
  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div className={styles.overlay}>
          <motion.div className={styles.modal}>
            {/* Conteúdo do modal */}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.getElementById('modal-root')!
  );
}
```

#### 2. Design do Modal - Usando skill frontend-design
- **Layout**: Modal centralizado com largura máxima de 600px
- **Header**: Título gradiente com ícone decorativo
- **Corpo**:
  - Input de título com design glassmorphism
  - Textarea expandível para descrição
  - Seleção de modelos em grid visual com cards
  - Área de upload com drag-and-drop
  - Preview de imagens em grid com efeitos hover
- **Footer**: Botões de ação com gradientes e animações

#### 3. Seleção de Modelos Redesenhada
```typescript
// ModelSelector component dentro do modal
const ModelCard = ({ model, selected, onChange }) => (
  <div className={`${styles.modelCard} ${selected ? styles.selected : ''}`}>
    <div className={styles.modelIcon}>
      {/* Ícone específico do modelo */}
    </div>
    <h4>{model.label}</h4>
    <p className={styles.modelDescription}>
      {model.description}
    </p>
    <div className={styles.modelBadge}>
      {model.speed} • {model.quality}
    </div>
  </div>
);
```

#### 4. Animações e Transições
```css
/* Entrada do modal */
@keyframes modalSlideUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Overlay com backdrop-filter */
.overlay {
  backdrop-filter: blur(10px) saturate(150%);
  background: rgba(10, 10, 15, 0.8);
}
```

#### 5. Upload de Imagens Melhorado
- Área de drag-and-drop visual
- Indicadores de progresso circulares
- Preview com zoom on hover
- Suporte para paste de imagens mantido
- Validação visual de tipos de arquivo

---

## 4. Testes

### Unitários
- [x] Modal abre e fecha corretamente
- [x] Validação de campos obrigatórios funciona
- [x] Upload de imagens processa corretamente
- [x] Seleção de modelos atualiza estado
- [x] ESC fecha o modal
- [x] Click fora fecha o modal

### Integração
- [x] Card é criado com sucesso via API
- [x] Novo card aparece na coluna backlog
- [x] Imagens são enviadas e associadas ao card
- [x] Reload da página mantém cards criados

---

## 5. Considerações

- **Performance:** Usar React.memo para componentes pesados e lazy loading para imagens
- **Acessibilidade:** Implementar trap de foco, aria-labels e navegação por teclado
- **Responsividade:** Modal deve adaptar para telas menores (mobile-first)
- **UX:** Adicionar feedback visual durante o envio (loading states)
- **Compatibilidade:** Testar em diferentes navegadores para backdrop-filter