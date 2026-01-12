# Guia de Contribuição

Obrigado por considerar contribuir para o Zenflow! Este documento fornece diretrizes para contribuir com o projeto.

## 📋 Código de Conduta

- Seja respeitoso e inclusivo
- Aceite críticas construtivas
- Foque no que é melhor para a comunidade
- Mostre empatia com outros membros da comunidade

## 🚀 Como Contribuir

### Reportando Bugs

Antes de criar um bug report:
1. Verifique se o bug já foi reportado nas [Issues](https://github.com/seu-usuario/zenflow/issues)
2. Verifique se está usando a versão mais recente

Use o template de bug report e inclua:
- Descrição clara do problema
- Passos para reproduzir
- Comportamento esperado vs atual
- Screenshots (se aplicável)
- Ambiente (OS, versões do Python/Node)

### Sugerindo Features

Use o template de feature request e inclua:
- Descrição clara da feature
- Motivação e use cases
- Possíveis implementações
- Impacto em funcionalidades existentes

### Pull Requests

1. **Fork o repositório**
   ```bash
   git clone https://github.com/seu-usuario/zenflow.git
   cd zenflow
   ```

2. **Crie uma branch**
   ```bash
   git checkout -b feature/minha-feature
   # ou
   git checkout -b fix/meu-bug
   ```

3. **Faça suas alterações**
   - Siga os padrões de código do projeto
   - Adicione testes se aplicável
   - Atualize documentação se necessário

4. **Commit suas alterações**
   ```bash
   git commit -m "feat: adiciona nova feature"
   # ou
   git commit -m "fix: corrige bug na autenticação"
   ```

   Use [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - Nova feature
   - `fix:` - Correção de bug
   - `docs:` - Mudanças na documentação
   - `style:` - Formatação, sem mudanças de código
   - `refactor:` - Refatoração de código
   - `test:` - Adição de testes
   - `chore:` - Manutenção geral

5. **Push para sua fork**
   ```bash
   git push origin feature/minha-feature
   ```

6. **Abra um Pull Request**
   - Descreva as mudanças claramente
   - Referencie issues relacionadas
   - Aguarde review

## 🏗️ Estrutura do Projeto

```
zenflow/
├── frontend/              # React + TypeScript
│   ├── src/
│   │   ├── components/   # Componentes React
│   │   ├── pages/        # Páginas
│   │   ├── services/     # Serviços de API
│   │   └── styles/       # CSS Modules
│   └── package.json
├── backend/              # FastAPI + Python
│   ├── src/
│   │   ├── api/         # Endpoints da API
│   │   ├── config/      # Configurações
│   │   ├── models/      # Modelos de dados
│   │   └── services/    # Lógica de negócio
│   └── requirements.txt
├── .claude/             # Claude Agent SDK
│   ├── commands/        # Comandos customizados
│   └── skills/          # Skills customizadas
└── docs/                # Documentação
```

## 💻 Ambiente de Desenvolvimento

### Configuração Inicial

```bash
# Instale dependências
npm run setup

# Inicie em modo desenvolvimento
npm run dev
```

### Testes

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Linting

```bash
# Backend
cd backend
ruff check .
black .

# Frontend
cd frontend
npm run lint
```

## 📝 Padrões de Código

### Python (Backend)

- Use **Type Hints** em todas as funções
- Siga **PEP 8**
- Use **Black** para formatação
- Máximo de 88 caracteres por linha

Exemplo:
```python
async def get_card(card_id: str, db: Session) -> Card:
    """Busca um card pelo ID."""
    return db.query(Card).filter(Card.id == card_id).first()
```

### TypeScript (Frontend)

- Use **TypeScript** estrito
- Componentes funcionais com **Hooks**
- Use **CSS Modules** para estilos
- Máximo de 100 caracteres por linha

Exemplo:
```typescript
interface CardProps {
  id: string;
  title: string;
  onUpdate: (id: string) => void;
}

export const Card: React.FC<CardProps> = ({ id, title, onUpdate }) => {
  return <div>{title}</div>;
};
```

## 🧪 Testes

### Backend
- Use **pytest** para testes
- Mínimo de 80% de coverage
- Teste casos de sucesso e erro

### Frontend
- Use **Vitest** para testes
- Teste componentes e hooks
- Teste integração com API

## 📚 Documentação

- Documente funções complexas
- Atualize README.md se necessário
- Adicione exemplos de uso
- Mantenha changelog atualizado

## 🔍 Review Process

1. **Automated Checks**
   - Linting passa
   - Testes passam
   - Build funciona

2. **Code Review**
   - Pelo menos 1 aprovação
   - Seguir padrões do projeto
   - Código limpo e legível

3. **Merge**
   - Squash commits se necessário
   - Merge para branch principal

## 🎯 Áreas para Contribuição

### Frontend
- [ ] Melhorias na UI/UX
- [ ] Novos componentes
- [ ] Otimizações de performance
- [ ] Responsividade mobile

### Backend
- [ ] Novos endpoints
- [ ] Otimizações de queries
- [ ] Melhorias de segurança
- [ ] Cache e performance

### Documentação
- [ ] Tutoriais
- [ ] Exemplos de uso
- [ ] Traduções
- [ ] Videos e screenshots

### Testes
- [ ] Aumentar coverage
- [ ] Testes E2E
- [ ] Testes de carga
- [ ] Testes de segurança

## 💬 Dúvidas?

- Abra uma [Discussion](https://github.com/seu-usuario/zenflow/discussions)
- Entre no [Discord](https://discord.gg/seu-servidor)
- Envie um email para: seu-email@exemplo.com

## 🙏 Agradecimentos

Obrigado por contribuir! Toda ajuda é bem-vinda e valorizada.
