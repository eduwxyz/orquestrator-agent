# Spec: Enhanced Execution Logs Modal

**Tipo:** Feature
**Criado em:** 2024-12-28

---

## 1. Resumo

Aprimorar a experiência de visualização de logs de execução através de um modal redesenhado com estética minimalista editorial, exibindo informações contextuais expandidas (metadados, duração, timestamps), formatação aprimorada de logs, e preservação do scroll do background. O modal seguirá princípios de **Editorial Minimalism**, inspirado em ferramentas modernas como Linear e Raycast, com tipografia refinada, progressive disclosure de informações, e micro-interações sutis mas impactantes.

**Problema:** O modal atual de logs é funcional mas básico, exibindo apenas timestamp, tipo e conteúdo dos logs sem contexto adicional sobre a execução (duração total, quando iniciou/terminou, metadados). Além disso, a experiência visual pode ser melhorada com uma hierarquia mais clara e formatação mais sofisticada.

**Solução:** Redesenhar o `LogsModal` para incluir uma seção de metadados contextual no topo, melhorar a formatação visual dos logs com syntax highlighting e agrupamento, e garantir que o scroll da página principal seja preservado quando o modal abrir.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Adicionar seção de metadados de execução (timestamp de início/fim, duração total, status)
- [x] Implementar formatação aprimorada de logs com cores contextuais e agrupamento visual
- [x] Melhorar tipografia e espaçamento seguindo princípios de Editorial Minimalism
- [x] Preservar scroll da página principal quando modal abre/fecha
- [x] Adicionar micro-interações e transições suaves para progressive disclosure
- [x] Implementar syntax highlighting básico para logs de código/JSON

### Fora do Escopo
- Exportação de logs para arquivo
- Filtros avançados de logs (por tipo, data, etc.)
- Busca dentro dos logs
- Logs em tempo real com websockets (manter polling atual)

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/LogsModal/LogsModal.tsx` | Modificar | Adicionar seção de metadados, melhorar estrutura do modal, implementar formatação avançada de logs |
| `frontend/src/components/LogsModal/LogsModal.module.css` | Modificar | Redesenhar estilos com Editorial Minimalism, adicionar animações e transições |
| `frontend/src/types/index.ts` | Modificar | Estender `ExecutionStatus` com campos de metadata (`startedAt`, `completedAt`, `duration`) |
| `backend/src/execution.py` | Modificar | Atualizar `ExecutionRecord` para incluir timestamps de início/fim |
| `backend/src/agent.py` | Modificar | Garantir que timestamps sejam salvos corretamente ao iniciar/completar execução |

### Detalhes Técnicos

#### 3.1 Extensão do Type System (Frontend + Backend)

**Frontend - `types/index.ts`:**
```typescript
export interface ExecutionStatus {
  cardId: string;
  status: 'idle' | 'running' | 'success' | 'error';
  result?: string;
  logs: ExecutionLog[];
  // Novos campos de metadados
  startedAt?: string; // ISO timestamp
  completedAt?: string; // ISO timestamp
  duration?: number; // milissegundos
}
```

**Backend - `execution.py`:** (já possui `startedAt` e `completedAt`, garantir que sejam enviados)
```python
class ExecutionRecord(CamelCaseModel):
    card_id: str = Field(alias="cardId")
    title: Optional[str] = None
    started_at: str = Field(alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    status: ExecutionStatus
    logs: list[ExecutionLog] = []
    result: Optional[str] = None
```

Garantir que o backend retorne `startedAt` e `completedAt` nas respostas de API.

#### 3.2 Estrutura do Modal Aprimorado

O modal terá três seções principais:

```tsx
<div className={styles.modal}>
  {/* 1. Header com título e controles */}
  <div className={styles.header}>
    <div className={styles.titleSection}>...</div>
    <div className={styles.controls}>...</div>
  </div>

  {/* 2. Metadata Panel (novo) - Progressive disclosure */}
  <div className={styles.metadataPanel}>
    <MetadataSection
      startedAt={executionStatus.startedAt}
      completedAt={executionStatus.completedAt}
      duration={executionStatus.duration}
      status={status}
    />
  </div>

  {/* 3. Logs Container - Formatação aprimorada */}
  <div className={styles.logsContainer}>
    <LogEntries logs={logs} />
  </div>
</div>
```

#### 3.3 Seção de Metadados (MetadataSection)

Componente interno ou seção no LogsModal que exibe:

```tsx
interface MetadataSectionProps {
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  status: 'idle' | 'running' | 'success' | 'error';
}

function MetadataSection({ startedAt, completedAt, duration, status }: MetadataSectionProps) {
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const mins = Math.floor(ms / 60000);
    const secs = Math.floor((ms % 60000) / 1000);
    return `${mins}m ${secs}s`;
  };

  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString('pt-BR', {
      dateStyle: 'short',
      timeStyle: 'medium'
    });
  };

  return (
    <div className={styles.metadata}>
      <MetadataItem
        icon={<ClockIcon />}
        label="Iniciado em"
        value={startedAt ? formatDateTime(startedAt) : '-'}
      />
      {completedAt && (
        <MetadataItem
          icon={<CheckCircleIcon />}
          label="Concluído em"
          value={formatDateTime(completedAt)}
        />
      )}
      {duration !== undefined && (
        <MetadataItem
          icon={<TimerIcon />}
          label="Duração"
          value={formatDuration(duration)}
          highlight
        />
      )}
      <MetadataItem
        icon={<StatusIcon />}
        label="Status"
        value={<StatusBadge status={status} />}
      />
    </div>
  );
}
```

**Ícones SVG inline minimalistas** (estilo Linear):
- Clock: linha fina, circular
- CheckCircle: círculo + checkmark
- Timer: ampulheta simplificada
- Status: dot indicator

#### 3.4 Formatação Aprimorada de Logs

**Agrupamento por tipo:**
```tsx
function LogEntries({ logs }: { logs: ExecutionLog[] }) {
  // Agrupar logs consecutivos do mesmo tipo
  const groupedLogs = useMemo(() => {
    const groups: LogGroup[] = [];
    let currentGroup: LogGroup | null = null;

    logs.forEach((log) => {
      if (!currentGroup || currentGroup.type !== log.type) {
        currentGroup = { type: log.type, entries: [log] };
        groups.push(currentGroup);
      } else {
        currentGroup.entries.push(log);
      }
    });

    return groups;
  }, [logs]);

  return (
    <div className={styles.logGroups}>
      {groupedLogs.map((group, idx) => (
        <LogGroup key={idx} group={group} />
      ))}
    </div>
  );
}
```

**Syntax highlighting básico:**
```tsx
function formatLogContent(content: string, type: LogType): React.ReactNode {
  // Detectar JSON e formatar
  if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
    try {
      const parsed = JSON.parse(content);
      return <pre className={styles.jsonContent}>{JSON.stringify(parsed, null, 2)}</pre>;
    } catch {}
  }

  // Detectar caminhos de arquivo e destacar
  const withHighlightedPaths = content.replace(
    /([\w\/\-\.]+\.(ts|tsx|js|jsx|py|md|json))/g,
    '<span class="file-path">$1</span>'
  );

  return <span dangerouslySetInnerHTML={{ __html: withHighlightedPaths }} />;
}
```

#### 3.5 Preservação de Scroll

**Problema:** Quando o modal abre, o `document.body.style.overflow = 'hidden'` previne scroll, mas ao fechar pode haver um "jump".

**Solução:**
```tsx
function LogsModal({ isOpen, onClose, ... }: LogsModalProps) {
  const scrollPositionRef = useRef(0);

  useEffect(() => {
    if (isOpen) {
      // Salvar posição atual do scroll
      scrollPositionRef.current = window.scrollY;

      // Prevenir scroll do body
      document.body.style.overflow = 'hidden';
      document.body.style.position = 'fixed';
      document.body.style.top = `-${scrollPositionRef.current}px`;
      document.body.style.width = '100%';
    }

    return () => {
      // Restaurar scroll
      document.body.style.overflow = '';
      document.body.style.position = '';
      document.body.style.top = '';
      document.body.style.width = '';
      window.scrollTo(0, scrollPositionRef.current);
    };
  }, [isOpen]);

  // ... resto do componente
}
```

#### 3.6 Estética Editorial Minimalism (CSS)

**Princípios de Design:**
1. **Tipografia Refinada**: Usar `--font-display` (Outfit) para títulos e metadados, `--font-mono` (SF Mono) para logs
2. **Espaçamento Generoso**: Aumentar padding e gaps entre elementos
3. **Hierarquia Visual Clara**: Metadados em grid, logs com indentação e separadores sutis
4. **Micro-interações**: Fade-in suave de metadados (staggered), hover states refinados
5. **Cores Contextuais**: Usar paleta cosmic dark existente com acentos sutis

**Estrutura CSS:**
```css
/* Modal base - aumentar max-width e height */
.modal {
  background: var(--bg-elevated);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 900px; /* aumentado de 800px */
  max-height: 85vh; /* aumentado de 80vh */
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl), var(--shadow-glow);
  border: 1px solid var(--border-default);
  animation: modalSlideUp 0.4s var(--ease-out);
}

@keyframes modalSlideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Header refinado */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
}

.titleSection {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.cardTitle {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* Metadata Panel */
.metadataPanel {
  padding: 20px 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.metadata {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.metadataItem {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  transition: all var(--duration-fast) var(--ease-out);
  animation: fadeInUp 0.3s var(--ease-out);
  animation-fill-mode: both;
}

.metadataItem:nth-child(1) { animation-delay: 0.05s; }
.metadataItem:nth-child(2) { animation-delay: 0.1s; }
.metadataItem:nth-child(3) { animation-delay: 0.15s; }
.metadataItem:nth-child(4) { animation-delay: 0.2s; }

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.metadataItem:hover {
  background: var(--bg-hover);
  border-color: var(--border-default);
}

.metadataIcon {
  width: 18px;
  height: 18px;
  color: var(--accent-cyan);
  flex-shrink: 0;
}

.metadataContent {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metadataLabel {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.metadataValue {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.metadataItem.highlight .metadataValue {
  color: var(--accent-cyan);
}

/* Logs Container refinado */
.logsContainer {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.7;
}

/* Log Groups */
.logGroup {
  margin-bottom: 16px;
}

.logGroupHeader {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  padding: 6px 12px;
  background: var(--bg-surface);
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Log Entries */
.logEntry {
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  background: var(--glass-bg);
  border-left: 2px solid transparent;
  transition: all var(--duration-fast) var(--ease-out);
  word-break: break-word;
}

.logEntry:hover {
  background: var(--bg-surface);
  border-left-color: var(--accent-cyan);
  transform: translateX(2px);
}

.timestamp {
  color: var(--text-dim);
  flex-shrink: 0;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.logType {
  flex-shrink: 0;
  font-weight: 700;
  font-size: 11px;
  min-width: 60px;
  text-align: right;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.logContent {
  color: var(--text-secondary);
  white-space: pre-wrap;
}

/* Cores contextuais por tipo de log */
.logInfo .logType { color: var(--accent-cyan); }
.logInfo:hover { border-left-color: var(--accent-cyan); }

.logTool .logType { color: var(--accent-purple); }
.logTool:hover { border-left-color: var(--accent-purple); }

.logText .logType { color: var(--accent-green); }
.logText:hover { border-left-color: var(--accent-green); }

.logError .logType { color: var(--accent-rose); }
.logError .logContent { color: var(--accent-rose); }
.logError:hover {
  border-left-color: var(--accent-rose);
  background: rgba(251, 113, 133, 0.05);
}

.logResult .logType { color: var(--accent-amber); }
.logResult:hover { border-left-color: var(--accent-amber); }

/* Syntax highlighting */
.jsonContent {
  margin-top: 6px;
  padding: 12px;
  background: var(--bg-deep);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  font-size: 12px;
  overflow-x: auto;
}

.logContent :global(.file-path) {
  color: var(--accent-cyan);
  font-weight: 600;
}
```

#### 3.7 Calcular Duração no Frontend

Como o backend já retorna `startedAt` e `completedAt`, podemos calcular a duração no frontend:

```tsx
const calculateDuration = (startedAt?: string, completedAt?: string): number | undefined => {
  if (!startedAt) return undefined;

  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();

  return end - start;
};

// No componente LogsModal
const duration = calculateDuration(executionStatus.startedAt, executionStatus.completedAt);
```

#### 3.8 Garantir Backend Retorna Metadados

Verificar que as rotas de API (`/api/execute-plan`, `/api/execute-implement`, etc.) retornem `startedAt` e `completedAt`:

```python
# backend/src/agent.py - já implementado, apenas verificar
async def execute_plan(...) -> PlanResult:
    record = ExecutionRecord(
        cardId=card_id,
        title=title,
        startedAt=datetime.now().isoformat(),  # ✅
        status=ExecutionStatus.RUNNING,
        logs=[],
    )

    # ... execução ...

    record.completedAt = datetime.now().isoformat()  # ✅
    record.status = ExecutionStatus.SUCCESS  # ou ERROR

    return PlanResult(...)
```

---

## 4. Testes

### Unitários
- [x] Teste de formatação de duração (`formatDuration`)
  - Duração < 1s: exibir em milissegundos
  - Duração < 1min: exibir em segundos
  - Duração >= 1min: exibir em minutos e segundos
- [x] Teste de agrupamento de logs (`groupedLogs`)
  - Logs consecutivos do mesmo tipo devem ser agrupados
  - Mudança de tipo deve criar novo grupo
- [x] Teste de preservação de scroll
  - Verificar que `scrollPositionRef` salva a posição correta
  - Verificar que scroll é restaurado após fechar modal

### Integração (Manual)
- [ ] Abrir modal de logs de uma execução completa
  - Verificar que metadados são exibidos corretamente
  - Verificar que duração é calculada e formatada
  - Verificar que logs são agrupados e formatados
- [ ] Abrir modal de logs de uma execução em andamento
  - Verificar que `completedAt` não é exibido
  - Verificar que duração é calculada até o momento atual
- [ ] Scroll preservation
  - Scrollar a página principal para baixo
  - Abrir modal de logs
  - Verificar que página não "pula"
  - Fechar modal
  - Verificar que scroll volta para a posição original
- [ ] Animações e transições
  - Verificar fade-in suave do modal
  - Verificar stagger animation dos metadados
  - Verificar hover states dos logs
- [ ] Responsividade
  - Testar em telas menores (tablet, mobile)
  - Verificar que grid de metadados adapta corretamente
  - Verificar que modal não ultrapassa viewport

### Visual/Acessibilidade
- [ ] Verificar contraste de cores (WCAG AA)
- [ ] Testar navegação por teclado (Tab, Escape)
- [ ] Verificar que ícones SVG têm `aria-label` quando necessário
- [ ] Testar leitores de tela (VoiceOver/NVDA)

---

## 5. Considerações

### Riscos
- **Complexidade visual excessiva**: Ao adicionar metadados e formatação avançada, existe o risco de sobrecarregar visualmente o modal. Mitigação: Seguir princípios de Editorial Minimalism com espaçamento generoso e hierarquia clara.
- **Performance com logs longos**: Agrupamento e formatação de milhares de logs pode ser lento. Mitigação: Usar `useMemo` para agrupamento e considerar virtualização (react-window) se necessário no futuro.
- **Inconsistência de dados**: Backend pode não retornar `startedAt`/`completedAt` em execuções antigas. Mitigação: Tratar campos como opcionais e exibir `-` quando ausentes.

### Dependências
- Nenhuma biblioteca externa necessária (tudo implementado com React + CSS)
- Backend já possui os campos necessários (`startedAt`, `completedAt`)
- Design tokens (CSS variables) já existem no `App.module.css`

### Performance
- Usar `useMemo` para agrupamento de logs
- Usar `useCallback` para handlers de eventos
- Considerar lazy loading de ícones SVG se forem muitos
- Evitar re-renders desnecessários com `React.memo` se necessário

### Melhorias Futuras (Fora do Escopo Atual)
- Exportar logs como arquivo `.txt` ou `.json`
- Filtros de logs por tipo, data, ou texto
- Busca dentro dos logs com highlight de resultados
- Modo de comparação (diff) entre execuções
- Gráfico de timeline visual da execução
- Logs em tempo real via WebSockets (atualmente usa polling)
- Modo escuro/claro toggle
- Copiar log individual ou todos os logs
