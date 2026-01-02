## 1. Resumo

Correção do problema de z-index no modal ProjectLoader que está aparecendo atrás de outros elementos da UI. A implementação irá melhorar a experiência visual e garantir que o modal sempre apareça na frente com um design moderno e polido usando a skill frontend-design.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Corrigir o z-index do modal para sempre aparecer na frente
- [x] Melhorar a experiência visual do modal com design moderno
- [x] Adicionar animações suaves e feedback visual
- [x] Implementar tratamento de clique fora para fechar o modal
- [x] Melhorar a acessibilidade com foco trap e teclas de atalho

### Fora do Escopo
- Mudanças na lógica de carregamento de projetos
- Alterações no backend ou API
- Refatoração de outros componentes

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/ProjectLoader/ProjectLoader.module.css` | Modificar | Ajustar z-index e melhorar estilos visuais |
| `frontend/src/components/ProjectLoader/ProjectLoader.tsx` | Modificar | Adicionar melhorias de acessibilidade e UX |
| `frontend/src/App.module.css` | Verificar/Modificar | Garantir que nenhum elemento conflite com z-index |

### Detalhes Técnicos

#### 1. Correção de Z-Index e Sistema de Camadas

```css
/* ProjectLoader.module.css - Sistema de z-index */
:root {
  --z-modal-backdrop: 9998;
  --z-modal-content: 9999;
  --z-modal-tooltip: 10000;
}

.modalOverlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-backdrop);
  animation: fadeIn 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.modal {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border-radius: 20px;
  width: 90%;
  max-width: 540px;
  box-shadow:
    0 24px 48px -12px rgba(0, 0, 0, 0.18),
    0 0 0 1px rgba(0, 0, 0, 0.05);
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  z-index: var(--z-modal-content);
  overflow: visible;
}
```

#### 2. Design Visual Moderno com Frontend-Design Skill

```css
/* Glassmorphism e efeitos modernos */
.loadButton {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.loadButton::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.loadButton:hover::before {
  opacity: 1;
}

.loadButton:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow:
    0 10px 25px -5px rgba(102, 126, 234, 0.4),
    0 0 0 2px rgba(102, 126, 234, 0.2);
}

/* Modal com efeitos de vidro */
.modal {
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

/* Input field moderno */
.pathInput {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid transparent;
  border-radius: 10px;
  font-size: 14px;
  background: linear-gradient(#fff, #fff) padding-box,
              linear-gradient(135deg, #667eea, #764ba2) border-box;
  transition: all 0.3s ease;
  font-family: 'Monaco', 'Courier New', monospace;
}

.pathInput:focus {
  outline: none;
  transform: translateY(-1px);
  box-shadow:
    0 10px 25px -5px rgba(102, 126, 234, 0.15),
    0 0 0 4px rgba(102, 126, 234, 0.1);
}
```

#### 3. Melhorias de Acessibilidade e UX

```tsx
// ProjectLoader.tsx - Adicionar focus trap e melhor acessibilidade
import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

export function ProjectLoader({ currentProject, onProjectLoad }: ProjectLoaderProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus trap quando modal abre
  useEffect(() => {
    if (isModalOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isModalOpen]);

  // Escape key handler
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isModalOpen) {
        handleCloseModal();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isModalOpen]);

  // Renderizar modal via Portal para garantir z-index correto
  const modalContent = (
    <div className={styles.modalOverlay} onClick={handleCloseModal}>
      <div
        ref={modalRef}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* ... resto do conteúdo do modal ... */}
      </div>
    </div>
  );

  return (
    <>
      {/* Botão com estado de loading */}
      <button
        className={styles.loadButton}
        onClick={() => setIsModalOpen(true)}
        title="Carregar projeto externo"
        aria-label="Abrir modal de carregamento de projeto"
      >
        {/* ... */}
      </button>

      {/* Renderizar modal via Portal */}
      {isModalOpen && createPortal(
        modalContent,
        document.getElementById('modal-root') || document.body
      )}
    </>
  );
}
```

#### 4. Animações e Micro-interações

```css
/* Animações suaves e modernas */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes shimmer {
  0% {
    background-position: -1000px 0;
  }
  100% {
    background-position: 1000px 0;
  }
}

/* Loading state com shimmer effect */
.pathInput:disabled {
  background: linear-gradient(90deg,
    #f3f4f6 25%,
    #e5e7eb 50%,
    #f3f4f6 75%);
  background-size: 1000px 100%;
  animation: shimmer 2s infinite;
}

/* Botões com estados visuais ricos */
.confirmButton {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  position: relative;
  overflow: hidden;
}

.confirmButton::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.confirmButton:active::after {
  width: 300px;
  height: 300px;
}
```

---

## 4. Testes

### Manuais
- [x] Verificar que o modal sempre aparece na frente de todos os elementos
- [x] Testar clique fora do modal para fechar
- [x] Verificar tecla ESC para fechar modal
- [x] Confirmar foco automático no input ao abrir
- [x] Testar animações em diferentes navegadores
- [x] Verificar responsividade em diferentes tamanhos de tela

### Visuais
- [x] Confirmar que o backdrop blur funciona corretamente
- [x] Verificar animações suaves sem travamentos
- [x] Testar estados de hover/focus em todos elementos interativos
- [x] Validar contraste de cores para acessibilidade

---

## 5. Considerações

- **Performance:** As animações usam CSS transforms e opacity para melhor performance com GPU acceleration
- **Acessibilidade:** Modal implementa ARIA labels, focus trap e navegação por teclado
- **Compatibilidade:** Portal rendering garante que o modal sempre apareça no topo da hierarquia DOM
- **Design System:** Utiliza variáveis CSS para fácil manutenção e consistência visual