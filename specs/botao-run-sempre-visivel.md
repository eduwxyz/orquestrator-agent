# Melhoria UI: Botão Run Sempre Visível

## 1. Resumo

Modificar a UI do botão "Run" nos cards da coluna backlog para que fique sempre visível no canto inferior direito do card, ao invés de aparecer somente quando o mouse passa sobre o card. Esta melhoria visa tornar a funcionalidade mais descobrível e acessível ao usuário, eliminando a necessidade de hover para visualizar uma ação primária importante.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Remover a dependência de hover para exibir o botão Run
- [x] Reposicionar o botão Run para o canto inferior direito do card
- [x] Manter a visibilidade do botão de remover (X) no canto superior direito
- [x] Garantir que o botão não interfira com o conteúdo do card (título, descrição)
- [x] Preservar o comportamento e funcionalidade existentes do botão
- [x] Manter consistência visual com o design system atual

### Fora do Escopo
- Alterações na funcionalidade do botão Run
- Alterações no botão "Create PR" da coluna Done
- Mudanças no botão de remover (X)
- Alterações no workflow de automação

---

## 3. Implementação

### Arquivos a Serem Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `frontend/src/components/Card/Card.module.css` | Modificar | Atualizar estilos do `.runButton` para posicionamento inferior direito e visibilidade permanente |
| `frontend/src/components/Card/Card.tsx` | Nenhuma | Não requer mudanças no JSX |

### Detalhes Técnicos

#### 3.1. Análise do Estado Atual

Atualmente, o botão Run possui os seguintes estilos (linhas 254-289 de `Card.module.css`):

```css
.runButton {
  position: absolute;
  top: 8px;              /* Posicionado no topo */
  right: 40px;           /* Lado direito, próximo ao botão X */
  padding: 4px 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
  opacity: 0;            /* Invisível por padrão */
  transform: scale(0.8); /* Escala reduzida quando invisível */
}

.card:hover .runButton {
  opacity: 1;            /* Aparece no hover */
  transform: scale(1);
}
```

**Problemas identificados:**
- `opacity: 0` torna o botão invisível por padrão
- `.card:hover .runButton` controla a visibilidade baseado em hover
- Posicionamento `top: 8px` coloca no topo do card

#### 3.2. Mudanças Necessárias

**Card.module.css - Atualizar estilos do `.runButton`**

Substituir o bloco de estilos `.runButton` (linhas 254-289) por:

```css
/* Run Button Styles */
.runButton {
  position: absolute;
  bottom: 8px;           /* Mudança: posicionar na parte inferior */
  right: 8px;            /* Mudança: canto direito (não precisa evitar botão X) */
  padding: 6px 10px;     /* Mudança: padding ligeiramente maior para destaque */
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;    /* Mudança: border-radius ligeiramente maior */
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;
  z-index: 10;
  opacity: 1;            /* Mudança: sempre visível */
  transform: scale(1);   /* Mudança: escala normal por padrão */
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2); /* Mudança: sombra sutil para destaque */
}

/* Remover o bloco .card:hover .runButton */

.runButton:hover {
  transform: translateY(-2px) scale(1.05); /* Mudança: efeito hover mais pronunciado */
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); /* Mudança: sombra mais forte no hover */
}

.runButton:active {
  transform: translateY(0) scale(0.98); /* Adição: feedback visual ao clicar */
}

.runButton svg {
  width: 12px;
  height: 12px;
}
```

**Mudanças detalhadas:**

1. **Posicionamento:**
   - `top: 8px` → `bottom: 8px`: Move para o canto inferior
   - `right: 40px` → `right: 8px`: Posiciona no canto direito (não há conflito com botão X que fica no topo)

2. **Visibilidade:**
   - `opacity: 0` → `opacity: 1`: Sempre visível
   - `transform: scale(0.8)` → `transform: scale(1)`: Escala normal
   - Remover regra `.card:hover .runButton`: Não depende mais de hover

3. **Visual:**
   - `padding: 4px 8px` → `padding: 6px 10px`: Aumenta área de clique
   - `border-radius: 4px` → `border-radius: 6px`: Cantos mais arredondados
   - Adicionar `box-shadow` padrão para destaque visual
   - Melhorar efeito hover com elevação (`translateY(-2px)`) e escala (`scale(1.05)`)
   - Adicionar estado `:active` para feedback tátil

#### 3.3. Considerações de Layout

**Espaçamento do conteúdo:**

Verificar se é necessário ajustar o padding inferior do `.content` para evitar que o texto da descrição sobreponha o botão. Atualmente:

```css
.content {
  position: relative;
  padding-right: var(--space-8);
  z-index: 1;
}
```

**Recomendação:** Adicionar `padding-bottom` ao `.content` quando o botão Run estiver presente:

```css
.content {
  position: relative;
  padding-right: var(--space-8);
  padding-bottom: 40px; /* Espaço para o botão Run */
  z-index: 1;
}
```

**IMPORTANTE:** Esta mudança deve ser aplicada somente se houver sobreposição visual. Recomenda-se testar primeiro sem essa alteração.

#### 3.4. Responsividade

O botão deve funcionar bem em diferentes tamanhos de card. Como está usando unidades fixas (`px`), deve permanecer consistente. Porém, em cards muito estreitos, considerar usar `right: 4px` e `bottom: 4px` em media queries:

```css
@media (max-width: 768px) {
  .runButton {
    right: 4px;
    bottom: 4px;
    padding: 4px 8px;
    font-size: 11px;
  }
}
```

**OPCIONAL:** Implementar somente se houver feedback de problemas em mobile/telas pequenas.

---

## 4. Testes

### Testes Visuais
- [ ] Verificar que o botão Run aparece sempre visível em cards na coluna Backlog
- [ ] Verificar posicionamento no canto inferior direito
- [ ] Verificar que não há sobreposição com título ou descrição do card
- [ ] Verificar que o botão de remover (X) continua visível no canto superior direito
- [ ] Verificar que o efeito hover funciona corretamente (elevação e sombra)
- [ ] Verificar que o efeito de clique (active) funciona
- [ ] Verificar alinhamento em cards com diferentes tamanhos de conteúdo

### Testes Funcionais
- [ ] Clicar no botão Run executa o workflow normalmente
- [ ] Botão não aparece quando card está em outras colunas
- [ ] Botão não aparece quando workflow já está em execução (`isRunning === true`)
- [ ] Drag and drop do card não é afetado pela mudança de posição do botão

### Testes de Acessibilidade
- [ ] Verificar que `aria-label` e `title` continuam funcionando
- [ ] Verificar foco do teclado (Tab navigation)
- [ ] Verificar contraste de cores (botão roxo sobre fundo do card)

### Testes de Compatibilidade
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari
- [ ] Mobile (iOS/Android)

---

## 5. Considerações

### Design Rationale
- **Sempre visível:** Torna a funcionalidade de automação mais descobrível, especialmente para novos usuários
- **Canto inferior direito:** Posição clássica para ações primárias (similar a FABs em mobile apps)
- **Não conflita com botão X:** Botão X permanece no canto superior direito (padrão para ações destrutivas)
- **Sombra sutil:** Adiciona profundidade e destaque sem poluir visualmente

### Riscos
- **Poluição visual:** Botão sempre visível pode tornar cards mais "pesados" visualmente
  - **Mitigação:** Usar sombra sutil e manter tamanho compacto. Se usuário reportar, considerar reduzir opacidade para 0.85 em estado normal.

- **Conflito com conteúdo:** Em cards com descrições longas, botão pode sobrepor texto
  - **Mitigação:** Adicionar `padding-bottom` ao `.content` se necessário (ver seção 3.3)

- **Inconsistência com botão Create PR:** Botão Create PR ainda usa hover
  - **Mitigação:** Este é um comportamento intencional - o botão Run é uma ação primária mais importante. Botão Create PR pode ser atualizado futuramente se houver demanda.

### Dependências
- Nenhuma dependência de backend
- Mudança puramente visual/CSS
- Não afeta tipos TypeScript ou hooks existentes

### Melhorias Futuras
- Aplicar o mesmo padrão (sempre visível no canto inferior direito) ao botão "Create PR" na coluna Done
- Adicionar animação de "pulse" no primeiro uso para chamar atenção do usuário
- Considerar adicionar tooltip informativo no primeiro hover
- Adicionar opção de configuração para usuário escolher entre "sempre visível" e "hover" (em Settings futuros)
