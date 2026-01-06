## 1. Resumo

Adicionar uma visualização animada (GIF-like) das mudanças de código no modal do card quando uma tarefa for finalizada na aba de review, mostrando arquivos adicionados/removidos e linhas modificadas com uma interface visualmente atrativa usando a skill frontend-design.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Capturar e armazenar informações de diff quando um card é movido para review/done
- [x] Criar componente de visualização de diff com animações suaves e design moderno
- [x] Integrar visualização no CardEditModal existente com nova aba "Changes"
- [x] Implementar API endpoints para captura e fornecimento de dados de diff
- [x] Utilizar skill frontend-design para criar uma UI distintiva e polida

### Fora do Escopo
- Modificação do fluxo de workflow existente
- Alteração na lógica de transição entre colunas
- Integração com sistemas de controle de versão externos (GitHub/GitLab)

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/schemas/card.py` | Modificar | Adicionar campos de diff ao schema do Card |
| `backend/src/models/card.py` | Modificar | Adicionar campos de diff ao modelo do Card |
| `backend/src/services/diff_analyzer.py` | Criar | Serviço para capturar e analisar diffs do git |
| `backend/src/routes/cards.py` | Modificar | Adicionar endpoint para atualizar diff quando card muda para review |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos TypeScript para dados de diff |
| `frontend/src/components/DiffVisualization/DiffVisualization.tsx` | Criar | Componente principal de visualização de diff |
| `frontend/src/components/DiffVisualization/DiffVisualization.module.css` | Criar | Estilos do componente de diff |
| `frontend/src/components/DiffVisualization/animations.ts` | Criar | Lógica de animações para o diff |
| `frontend/src/components/CardEditModal/CardEditModal.tsx` | Modificar | Adicionar aba "Changes" com DiffVisualization |
| `frontend/src/hooks/useDiffAnimation.ts` | Criar | Hook customizado para controlar animações do diff |

### Detalhes Técnicos

#### 1. Backend - Modelo de Dados de Diff

```python
# backend/src/schemas/card.py
class DiffStats(BaseModel):
    files_added: List[str] = []
    files_modified: List[str] = []
    files_removed: List[str] = []
    lines_added: int = 0
    lines_removed: int = 0
    total_changes: int = 0
    captured_at: Optional[str] = None
    branch_name: Optional[str] = None

class CardSchema(BaseModel):
    # ... campos existentes ...
    diff_stats: Optional[DiffStats] = None
```

#### 2. Backend - Serviço de Análise de Diff

```python
# backend/src/services/diff_analyzer.py
class DiffAnalyzer:
    async def capture_diff(self, worktree_path: str, branch_name: str) -> DiffStats:
        """Captura estatísticas de diff de um worktree."""
        # Executar git diff --stat
        # Executar git diff --name-status
        # Processar e retornar DiffStats
        pass

    async def get_detailed_diff(self, worktree_path: str, file_path: str) -> str:
        """Obtém diff detalhado de um arquivo específico."""
        # Executar git diff para arquivo específico
        pass
```

#### 3. Frontend - Componente de Visualização com Design Distintivo

```typescript
// frontend/src/components/DiffVisualization/DiffVisualization.tsx
interface DiffVisualizationProps {
  diffStats: DiffStats | null;
  isAnimating?: boolean;
}

export function DiffVisualization({ diffStats, isAnimating }: DiffVisualizationProps) {
  // Usar skill frontend-design para criar visualização única
  // Incluir:
  // - Cards animados para arquivos adicionados/removidos
  // - Gráfico de barras animado para linhas modificadas
  // - Transições suaves entre estados
  // - Paleta de cores distintiva (verde para adições, vermelho para remoções)
  // - Ícones e micro-interações
}
```

#### 4. Frontend - Hook de Animação

```typescript
// frontend/src/hooks/useDiffAnimation.ts
export function useDiffAnimation(diffStats: DiffStats | null) {
  const [animationState, setAnimationState] = useState<'idle' | 'playing' | 'paused'>('idle');
  const [currentFrame, setCurrentFrame] = useState(0);

  // Controlar sequência de animação
  // Frame 1: Mostrar arquivos adicionados (fade in com bounce)
  // Frame 2: Mostrar arquivos modificados (slide in)
  // Frame 3: Mostrar arquivos removidos (fade out com scale)
  // Frame 4: Animar contadores de linhas (count up)

  return { animationState, currentFrame, play, pause, reset };
}
```

#### 5. Frontend - Integração no CardEditModal

```typescript
// frontend/src/components/CardEditModal/CardEditModal.tsx
export function CardEditModal({ ... }) {
  const [activeTab, setActiveTab] = useState<'details' | 'images' | 'changes'>('details');

  return (
    <div className={styles.modal}>
      {/* Tabs navigation */}
      <div className={styles.tabs}>
        <button onClick={() => setActiveTab('details')}>Details</button>
        <button onClick={() => setActiveTab('images')}>Images</button>
        {card.columnId === 'review' || card.columnId === 'done' ? (
          <button onClick={() => setActiveTab('changes')}>
            Changes {card.diffStats && (
              <span className={styles.changeBadge}>
                +{card.diffStats.lines_added} -{card.diffStats.lines_removed}
              </span>
            )}
          </button>
        ) : null}
      </div>

      {/* Tab content */}
      {activeTab === 'changes' && (
        <DiffVisualization
          diffStats={card.diffStats}
          isAnimating={true}
        />
      )}
    </div>
  );
}
```

---

## 4. Testes

### Unitários
- [ ] Testar DiffAnalyzer.capture_diff com diferentes estados de git
- [ ] Testar parsing de git diff output
- [ ] Testar componente DiffVisualization com diferentes props
- [ ] Testar hook useDiffAnimation e sequência de frames
- [ ] Testar integração de tabs no CardEditModal

### Integração
- [ ] Testar captura automática de diff quando card move para review
- [ ] Testar persistência de dados de diff no banco
- [ ] Testar carregamento e exibição de diff no frontend
- [ ] Testar animações e transições visuais

---

## 5. Considerações

- **Performance:** Animações devem usar CSS transforms e opacity para melhor performance
- **Acessibilidade:** Incluir aria-labels e suporte a prefers-reduced-motion
- **Cache:** Armazenar diff capturado para evitar recálculos
- **Limites:** Limitar visualização a primeiros 100 arquivos para grandes mudanças
- **Fallback:** Mostrar mensagem apropriada se diff não disponível
- **Design System:** Usar skill frontend-design para criar componentes visualmente distintivos que evitem estética genérica de IA