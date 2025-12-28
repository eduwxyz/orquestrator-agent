# Plano: Mudar Título de "Kanban Board" para "Board Kanban"

**Tipo:** Refactor
**Data:** 2025-01-23

---

## 1. Resumo

Atualizar o título da aplicação de "Kanban Board" (inglês) para "Board Kanban" (português) em todos os locais onde aparece, garantindo consistência com o fato de que a interface já utiliza `lang="pt-BR"` e mantendo coerência linguística em toda a aplicação.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Alterar o título no HTML (`<title>`) de "Kanban Board" para "Board Kanban"
- [x] Alterar o título do header em `App.tsx` de "Kanban Board" para "Board Kanban"
- [x] Atualizar a descrição no `package.json` para português
- [x] Garantir consistência linguística em português brasileiro

### Fora do Escopo
- Tradução de variáveis, nomes de classes ou identificadores técnicos no código
- Alteração de comentários em código (podem permanecer em inglês se preferido)
- Modificação de dependências ou funcionalidades

---

## 3. Implementação

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/index.html` | Modificar | Alterar `<title>Kanban Board</title>` para `<title>Board Kanban</title>` |
| `frontend/src/App.tsx` | Modificar | Alterar título do header de "Kanban Board" para "Board Kanban" |
| `package.json` | Modificar | Atualizar a descrição de "Kanban Board with Claude Agent integration" para português |

### Detalhes Técnicos

#### 1. frontend/index.html (linha 7)
```html
<!-- ANTES -->
<title>Kanban Board</title>

<!-- DEPOIS -->
<title>Board Kanban</title>
```

#### 2. frontend/src/App.tsx (linha 167)
```tsx
// ANTES
<h1 className={styles.title}>Kanban Board</h1>

// DEPOIS
<h1 className={styles.title}>Board Kanban</h1>
```

#### 3. package.json (linha 5)
```json
// ANTES
"description": "Kanban Board with Claude Agent integration",

// DEPOIS
"description": "Board Kanban com integração ao Claude Agent",
```

---

## 4. Testes

### Testes Manuais
- [x] Verificar que o título da aba do navegador mostra "Board Kanban"
- [x] Verificar que o header da aplicação mostra "Board Kanban"
- [x] Confirmar que não há erros de console no navegador
- [x] Testar se a aplicação continua funcionando normalmente após as alterações

### Verificação de Consistência
- [x] Buscar por outras ocorrências de "Kanban Board" no código
- [x] Garantir que a mudança foi aplicada em todos os locais visíveis ao usuário

---

## 5. Considerações

- **Riscos:** Nenhum risco identificado. Mudança puramente textual e cosmética
- **Impacto:** Mínimo. Não afeta funcionalidades, apenas textos visíveis
- **Consistência:** A alteração torna a aplicação mais consistente com o atributo `lang="pt-BR"` já definido no HTML
- **Reversibilidade:** Fácil reverter se necessário, apenas alterando os mesmos textos de volta
