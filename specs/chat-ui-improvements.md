## 1. Resumo

Melhorar a interface de chat do sistema corrigindo renderização de markdown, filtrando modelos disponíveis para mostrar apenas Anthropic e Gemini, e ajustando estilos para consistência com o design deep dark minimalist do projeto. A motivação é resolver problemas de UX identificados e alinhar a interface de chat com o padrão visual já estabelecido na aplicação.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Implementar renderização correta de markdown nas mensagens do chat
- [x] Filtrar modelos no seletor para exibir apenas Anthropic e Gemini (remover OpenAI GPT)
- [x] Ajustar estilos da UI de chat para manter consistência com o tema Deep Dark Minimalist
- [x] Melhorar a experiência geral de usuário na interface de chat
- [x] Adicionar suporte a formatação rica (code blocks, listas, links, etc.)

### Fora do Escopo
- Mudanças no backend ou API de chat
- Alterações na lógica de comunicação com modelos
- Modificações em outras páginas além da interface de chat
- Implementação de novos recursos funcionais de chat

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/package.json` | Modificar | Adicionar bibliotecas de markdown (react-markdown, remark-gfm) |
| `frontend/src/components/Chat/ChatMessage.tsx` | Modificar | Implementar renderização de markdown com componentes customizados |
| `frontend/src/components/Chat/ChatMessage.module.css` | Modificar | Adicionar estilos para elementos markdown |
| `frontend/src/components/Chat/ModelSelector.tsx` | Modificar | Filtrar array de modelos para exibir apenas Anthropic e Gemini |
| `frontend/src/components/Chat/Chat.module.css` | Modificar | Ajustar estilos para consistência com tema |
| `frontend/src/components/Chat/ChatInput.module.css` | Modificar | Ajustar estilos de input para melhor integração visual |
| `frontend/src/pages/ChatPage.module.css` | Modificar | Refinar estilos gerais da página de chat |
| `frontend/src/components/Chat/MarkdownComponents.tsx` | Criar | Componentes React customizados para renderização de markdown |
| `frontend/src/components/Chat/MarkdownComponents.module.css` | Criar | Estilos específicos para elementos markdown |

### Detalhes Técnicos

#### 1. Instalação de Dependências de Markdown
```bash
npm install react-markdown remark-gfm react-syntax-highlighter
npm install --save-dev @types/react-syntax-highlighter
```

#### 2. Componente de Renderização Markdown
```typescript
// MarkdownComponents.tsx
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import styles from './MarkdownComponents.module.css';

export const markdownComponents = {
  code({ inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || '');
    return !inline && match ? (
      <SyntaxHighlighter
        style={oneDark}
        language={match[1]}
        PreTag="div"
        className={styles.codeBlock}
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    ) : (
      <code className={styles.inlineCode} {...props}>
        {children}
      </code>
    );
  },
  p: ({ children }: any) => <p className={styles.paragraph}>{children}</p>,
  ul: ({ children }: any) => <ul className={styles.list}>{children}</ul>,
  ol: ({ children }: any) => <ol className={styles.orderedList}>{children}</ol>,
  li: ({ children }: any) => <li className={styles.listItem}>{children}</li>,
  blockquote: ({ children }: any) => (
    <blockquote className={styles.blockquote}>{children}</blockquote>
  ),
  h1: ({ children }: any) => <h1 className={styles.heading1}>{children}</h1>,
  h2: ({ children }: any) => <h2 className={styles.heading2}>{children}</h2>,
  h3: ({ children }: any) => <h3 className={styles.heading3}>{children}</h3>,
  a: ({ href, children }: any) => (
    <a href={href} className={styles.link} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  table: ({ children }: any) => (
    <div className={styles.tableWrapper}>
      <table className={styles.table}>{children}</table>
    </div>
  ),
};
```

#### 3. Atualização do ChatMessage.tsx
```typescript
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { markdownComponents } from './MarkdownComponents';

// No componente ChatMessage
<div className={styles.messageText}>
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={markdownComponents}
  >
    {message.content}
  </ReactMarkdown>
  {message.isStreaming && (
    <span className={styles.streamingCursor}>▊</span>
  )}
</div>
```

#### 4. Filtragem de Modelos no ModelSelector
```typescript
// ModelSelector.tsx
export const AVAILABLE_MODELS: AIModel[] = [
  // Modelos Anthropic
  {
    id: 'opus-4.5',
    name: 'Opus 4.5',
    displayName: 'Opus 4.5',
    provider: 'anthropic',
    maxTokens: 200000,
    description: 'Most powerful model for complex reasoning and advanced tasks',
    performance: 'powerful',
    icon: '🧠',
    accent: 'anthropic',
    badge: 'Most Capable'
  },
  // ... outros modelos Anthropic

  // Modelos Gemini
  {
    id: 'gemini-3-pro',
    name: 'Gemini 3 Pro',
    displayName: 'Gemini Pro',
    provider: 'google',
    maxTokens: 1000000,
    description: 'Google\'s most capable multimodal model with long context',
    performance: 'powerful',
    icon: '🌟',
    accent: 'google',
    badge: 'Long Context'
  },
  // ... outros modelos Gemini
].filter(model => model.provider === 'anthropic' || model.provider === 'google');
```

#### 5. Estilos Consistentes com Tema Deep Dark

```css
/* MarkdownComponents.module.css */
.paragraph {
  margin: var(--space-3) 0;
  line-height: 1.7;
  color: var(--text-primary);
}

.codeBlock {
  margin: var(--space-4) 0;
  border-radius: var(--radius-md);
  background: var(--bg-primary) !important;
  border: 1px solid var(--border-default);
  font-size: 0.9rem;
  overflow-x: auto;
}

.inlineCode {
  padding: 2px 6px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--accent-cyan);
  font-family: var(--font-mono);
  font-size: 0.85em;
}

.list {
  margin: var(--space-3) 0;
  padding-left: var(--space-5);
  color: var(--text-primary);
}

.listItem {
  margin: var(--space-1) 0;
  line-height: 1.7;
}

.listItem::marker {
  color: var(--accent-cyan);
}

.blockquote {
  margin: var(--space-4) 0;
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid var(--accent-primary);
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-style: italic;
}

.heading1, .heading2, .heading3 {
  margin-top: var(--space-5);
  margin-bottom: var(--space-3);
  font-weight: 600;
  color: var(--text-primary);
}

.heading1 {
  font-size: 1.5rem;
  border-bottom: 1px solid var(--border-default);
  padding-bottom: var(--space-2);
}

.heading2 {
  font-size: 1.25rem;
}

.heading3 {
  font-size: 1.1rem;
}

.link {
  color: var(--accent-cyan);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: all var(--duration-fast) var(--ease-out);
}

.link:hover {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

.tableWrapper {
  overflow-x: auto;
  margin: var(--space-4) 0;
}

.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.table th {
  background: var(--bg-elevated);
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-strong);
}

.table td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.table tr:last-child td {
  border-bottom: none;
}

.table tr:hover {
  background: var(--bg-elevated);
}
```

#### 6. Ajustes nos Estilos Existentes

Atualizar variáveis CSS para garantir consistência:
- Usar `var(--bg-tertiary)` para backgrounds de cards
- Usar `var(--border-default)` para bordas
- Usar `var(--accent-cyan)` e `var(--accent-primary)` para destaques
- Aplicar `backdrop-filter: blur()` para efeitos glass morphism
- Usar transições suaves com `var(--duration-normal)`

---

## 4. Testes

### Unitários
- [x] Teste de renderização de markdown básico (parágrafos, listas)
- [x] Teste de renderização de code blocks com syntax highlighting
- [x] Teste de filtragem de modelos (apenas Anthropic e Gemini aparecem)
- [x] Teste de elementos interativos (links externos abrem em nova aba)

### Integração
- [x] Verificar renderização correta de mensagens complexas com markdown misto
- [x] Testar responsividade em diferentes tamanhos de tela
- [x] Validar consistência visual com resto da aplicação
- [x] Testar performance com mensagens longas contendo muito markdown

### Testes Manuais
- [x] Enviar mensagem com markdown e verificar formatação
- [x] Verificar que modelos OpenAI não aparecem no seletor
- [x] Validar que tema dark é mantido em todos elementos
- [x] Testar copy/paste de código dos code blocks
- [x] Verificar acessibilidade com leitor de tela

---

## 5. Considerações

### Riscos
- **Performance**: Renderização de markdown muito complexo pode impactar performance
  - Mitigação: Implementar lazy loading para mensagens antigas e virtualização se necessário

- **Segurança**: Links maliciosos em markdown
  - Mitigação: Sanitizar HTML e sempre usar `rel="noopener noreferrer"` em links externos

- **Compatibilidade**: Diferentes navegadores podem renderizar elementos de forma diferente
  - Mitigação: Testar em Chrome, Firefox, Safari e Edge

### Dependências
- Aprovação para adicionar novas bibliotecas npm
- Validação de design com stakeholders
- Testes em ambiente de staging antes de produção

### Notas de Implementação
- Manter retrocompatibilidade com mensagens antigas sem markdown
- Considerar adicionar toggle para desabilitar formatação rica se necessário
- Documentar novos componentes de markdown para futura manutenção
- Garantir que dark mode seja respeitado em todos novos elementos