# Plano: Renomear Produto para Zenflow

## 1. Resumo

Atualizar o nome do produto em toda a aplicação de "Orquestrator Agent" e suas variações (Kanban Agent Orchestrator, Board Kanban, etc.) para "Zenflow", garantindo consistência em todos os arquivos, documentações, interfaces e configurações.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Renomear todas as referências do produto para "Zenflow"
- [x] Atualizar descrições para refletir o novo nome
- [x] Manter consistência de branding em toda aplicação
- [x] Preservar funcionalidades existentes durante a mudança

### Fora do Escopo
- Mudanças de funcionalidade
- Alterações de design além do nome
- Refatorações de código não relacionadas ao renaming
- Mudanças em URLs de repositório ou deployment

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `package.json` | Modificar | Atualizar nome e descrição do projeto raiz |
| `frontend/package.json` | Modificar | Renomear de "kanban-frontend" para "zenflow-frontend" |
| `backend/pyproject.toml` | Modificar | Renomear de "kanban-agent-server" para "zenflow-server" |
| `frontend/index.html` | Modificar | Atualizar título e meta description |
| `README.md` | Modificar | Atualizar todo o conteúdo com novo nome |
| `frontend/src/components/Navigation/Sidebar.tsx` | Modificar | Atualizar label do footer e navegação |
| `frontend/src/layouts/WorkspaceLayout.tsx` | Modificar | Atualizar breadcrumb e labels |
| `frontend/src/pages/SettingsPage.tsx` | Modificar | Atualizar placeholder e textos |
| `frontend/src/pages/KanbanPage.tsx` | Modificar | Atualizar título da página |
| `docs/CONTRIBUTING.md` | Modificar | Atualizar referências ao produto |
| `docs/MIGRATIONS.md` | Modificar | Atualizar referências ao produto |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Modificar | Atualizar nome do produto |

### Detalhes Técnicos

#### 1. Arquivos de Configuração Principal

**package.json (raiz)**
```json
{
  "name": "zenflow",
  "description": "Zenflow - Sistema inteligente de gestão de workflow com IA",
  // resto permanece igual
}
```

**frontend/package.json**
```json
{
  "name": "zenflow-frontend",
  // resto permanece igual
}
```

**backend/pyproject.toml**
```toml
[project]
name = "zenflow-server"
description = "Backend server for Zenflow - AI-powered workflow management"
```

#### 2. Interface HTML e Meta Tags

**frontend/index.html**
```html
<title>Zenflow - Workflow Inteligente</title>
<meta name="description" content="Zenflow - Sistema unificado de gestão de workflow com IA integrada para automação de desenvolvimento" />
```

#### 3. Componentes React

**frontend/src/components/Navigation/Sidebar.tsx**
```tsx
// Linha 52
<h2 className={styles.logoText}>Zenflow</h2>

// Linha 21 - Atualizar label do Kanban
{
  id: 'kanban',
  label: 'Workflow Board',
  icon: 'fa-solid fa-table-columns',
  description: 'Gerenciar tarefas e workflow',
}

// Linha 83
<span className={styles.footerLabel}>Zenflow</span>
```

**frontend/src/layouts/WorkspaceLayout.tsx**
```tsx
// Linha 15
kanban: 'Workflow Board',

// Linha 27
<span className={styles.breadcrumbItem}>Zenflow</span>
```

**frontend/src/pages/KanbanPage.tsx**
```tsx
// Linha 64
<h1 className={styles.kanbanTitle}>Workflow Board</h1>
```

**frontend/src/pages/SettingsPage.tsx**
```tsx
// Linha 47
<p className={styles.settingsSubtitle}>
  Gerencie as preferências do Zenflow
</p>

// Linha 80
placeholder="Zenflow"
```

#### 4. Documentação

**README.md**
```markdown
# 🚀 Zenflow

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![Node](https://img.shields.io/badge/node-18+-green)

Sistema inteligente de gestão de workflow com IA integrada. Gerencie seus projetos com automação inteligente executando tarefas através de cards no board.

## ✨ Features

- 📋 **Workflow Board Visual** - Interface moderna para gerenciamento de tarefas
- 🤖 **Claude Agent Integration** - Execute tarefas automaticamente com IA
- 🌲 **Git Worktree Automation** - Isolamento automático de branches
- 📊 **Métricas e Dashboard** - Acompanhe custos e progresso
- 💬 **Chat Integrado** - Converse com Claude sobre o projeto
- 🔄 **Workflow Automation** - Pipeline plan → implement → test → review → done

// Atualizar todo o resto do README com "Zenflow" ao invés de "Kanban Agent Orchestrator"
```

---

## 4. Testes

### Verificações Manuais
- [x] Verificar que o título da aba do navegador mostra "Zenflow - Workflow Inteligente"
- [x] Confirmar que o logo/nome no sidebar mostra "Zenflow"
- [x] Verificar breadcrumbs mostrando "Zenflow / [Módulo]"
- [x] Confirmar título "Workflow Board" no módulo Kanban
- [x] Verificar footer do sidebar mostrando "Zenflow v1.0.0"
- [x] Confirmar placeholder nas configurações mostrando "Zenflow"

### Testes de Integração
- [x] Verificar que o backend ainda responde corretamente
- [x] Confirmar que a comunicação frontend-backend não foi afetada
- [x] Testar que a integração com Claude Agent continua funcionando

---

## 5. Considerações

### Riscos
- **Documentação Externa**: Links ou referências externas ao projeto podem ficar desatualizados
- **Cache do Browser**: Usuários podem precisar limpar cache para ver as mudanças
- **Dependências**: Nome dos pacotes npm/pypi podem precisar ser atualizados no futuro

### Mitigação
- Fazer as mudanças de forma incremental e testar cada módulo
- Documentar claramente a mudança de nome em um CHANGELOG
- Considerar criar redirects ou aliases temporários se necessário

### Notas de Implementação
- Manter "Claude Agent" nas descrições técnicas onde apropriado, pois é o nome da tecnologia utilizada
- O termo "Kanban" pode ser substituído por "Workflow Board" para melhor alinhamento com o novo nome
- Preservar todas as funcionalidades existentes durante a renomeação