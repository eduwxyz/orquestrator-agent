# Auto-criar Card de Correção ao Falhar Teste

## 1. Resumo

Implementar funcionalidade que automaticamente cria um novo card de correção quando os testes de um card falharem, mantendo a relação entre o card original e o card de correção para rastreabilidade do processo de desenvolvimento.

---

## 2. Objetivos e Escopo

### Objetivos
- [x] Detectar falhas de teste durante a execução do comando `/test-implementation`
- [x] Criar automaticamente um novo card de correção com informações da falha
- [x] Estabelecer relação entre card original e card de correção
- [x] Incluir contexto do erro no novo card (logs, mensagens de erro)
- [x] Configurar o novo card com as mesmas configurações de modelo do card original

### Fora do Escopo
- Modificação do fluxo de execução de outros comandos (/plan, /implement, /review)
- Criação automática de cards para outros tipos de erro
- Modificação da interface visual dos cards no Kanban

---

## 3. Implementação

### Arquivos a Serem Modificados/Criados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `backend/src/models/card.py` | Modificar | Adicionar campo `parent_card_id` e `is_fix_card` para rastrear cards de correção |
| `backend/src/schemas/card.py` | Modificar | Adicionar campos no schema para suportar relação entre cards |
| `backend/src/repositories/card_repository.py` | Modificar | Adicionar método para criar card de correção |
| `backend/src/agent.py` | Modificar | Detectar falha de teste e criar card de correção |
| `backend/src/services/test_result_analyzer.py` | Criar | Serviço para analisar resultado dos testes e extrair informações relevantes |
| `backend/migrations/` | Criar | Migration para adicionar novos campos na tabela cards |
| `frontend/src/types/index.ts` | Modificar | Adicionar tipos para cards de correção |
| `frontend/src/components/Card/Card.tsx` | Modificar | Exibir indicador visual quando for card de correção |

### Detalhes Técnicos

#### 1. Modificação do Modelo Card

```python
# backend/src/models/card.py
class Card(Base):
    # ... campos existentes ...

    # Novos campos para rastreamento de correções
    parent_card_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("cards.id", ondelete="SET NULL"),
        nullable=True
    )
    is_fix_card: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    test_error_context: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Relacionamento auto-referencial
    parent_card = relationship("Card", back_populates="fix_cards", remote_side=[id])
    fix_cards = relationship("Card", back_populates="parent_card")
```

#### 2. Serviço de Análise de Resultados de Teste

```python
# backend/src/services/test_result_analyzer.py
from typing import Dict, Optional, List
import re

class TestResultAnalyzer:
    """Analisa resultados de teste e extrai informações relevantes."""

    @staticmethod
    def analyze_test_failure(logs: List[ExecutionLog]) -> Dict[str, any]:
        """
        Analisa logs de teste para extrair:
        - Tipo de erro (sintaxe, lógica, importação, etc)
        - Arquivos afetados
        - Mensagens de erro principais
        - Sugestões de correção
        """
        error_info = {
            "error_type": None,
            "affected_files": [],
            "error_messages": [],
            "test_failures": [],
            "suggestions": []
        }

        for log in logs:
            if log.type == "error":
                # Extrair tipo de erro
                if "SyntaxError" in log.content:
                    error_info["error_type"] = "syntax"
                elif "ImportError" in log.content:
                    error_info["error_type"] = "import"
                elif "test failed" in log.content.lower():
                    error_info["error_type"] = "test_failure"

                # Extrair arquivos mencionados
                files = re.findall(r'[a-zA-Z0-9_/]+\.(py|ts|tsx|js|jsx)', log.content)
                error_info["affected_files"].extend(files)

                # Coletar mensagens de erro
                error_info["error_messages"].append(log.content[:500])

        return error_info

    @staticmethod
    def generate_fix_description(error_info: Dict) -> str:
        """Gera descrição para o card de correção baseado no erro."""
        description_parts = [
            "## Contexto do Erro",
            f"Este card foi criado automaticamente devido a falhas nos testes.",
            ""
        ]

        if error_info["error_type"]:
            description_parts.append(f"**Tipo de erro:** {error_info['error_type']}")

        if error_info["affected_files"]:
            description_parts.append("\n**Arquivos afetados:**")
            for file in set(error_info["affected_files"]):
                description_parts.append(f"- {file}")

        if error_info["error_messages"]:
            description_parts.append("\n**Mensagens de erro:**")
            for msg in error_info["error_messages"][:3]:  # Limitar a 3 mensagens
                description_parts.append(f"```\n{msg}\n```")

        description_parts.append("\n## Ação Necessária")
        description_parts.append("Analise os erros acima e implemente as correções necessárias.")

        return "\n".join(description_parts)
```

#### 3. Modificação da Função execute_test_implementation

```python
# backend/src/agent.py
async def execute_test_implementation(
    card_id: str,
    spec_path: str,
    cwd: str,
    model: str = "opus-4.5",
    images: Optional[list] = None,
) -> PlanResult:
    # ... código existente de execução ...

    # Após a execução, verificar se houve falha
    if not result.success or record.status == ExecutionStatus.ERROR:
        # Analisar os logs para extrair informações do erro
        from .services.test_result_analyzer import TestResultAnalyzer
        analyzer = TestResultAnalyzer()
        error_info = analyzer.analyze_test_failure(record.logs)

        # Criar card de correção automaticamente
        async with async_session_maker() as session:
            repo = CardRepository(session)

            # Buscar card original para obter configurações
            original_card = await repo.get_by_id(card_id)

            if original_card:
                fix_description = analyzer.generate_fix_description(error_info)

                # Criar novo card de correção
                fix_card_data = CardCreate(
                    title=f"[FIX] {original_card.title[:50]}",
                    description=fix_description,
                    model_plan=original_card.model_plan,
                    model_implement=original_card.model_implement,
                    model_test=original_card.model_test,
                    model_review=original_card.model_review,
                    parent_card_id=card_id,
                    is_fix_card=True,
                    test_error_context=json.dumps(error_info)
                )

                fix_card = await repo.create(fix_card_data)
                await session.commit()

                add_log(
                    record,
                    LogType.INFO,
                    f"Card de correção criado automaticamente: {fix_card.id}"
                )

                # Adicionar informação do card de correção no resultado
                result.fix_card_id = fix_card.id

    return result
```

#### 4. Atualização do Frontend para Exibir Cards de Correção

```typescript
// frontend/src/types/index.ts
export interface Card {
  // ... campos existentes ...
  parentCardId?: string;
  isFixCard?: boolean;
  testErrorContext?: string;
}

// frontend/src/components/Card/Card.tsx
export function Card({ card, onEdit, onDelete, onMove, onExecute }: CardProps) {
  // ... código existente ...

  return (
    <div className={`${styles.card} ${card.isFixCard ? styles.fixCard : ''}`}>
      {card.isFixCard && (
        <div className={styles.fixBadge}>
          🔧 Correção
        </div>
      )}
      {/* ... resto do componente ... */}
    </div>
  );
}
```

---

## 4. Testes

### Unitários
- [x] Testar `TestResultAnalyzer.analyze_test_failure` com diferentes tipos de erro
- [x] Testar `TestResultAnalyzer.generate_fix_description` com diferentes contextos
- [x] Testar criação de card de correção no repositório
- [x] Testar relação entre card pai e card de correção

### Integração
- [x] Executar teste que falha e verificar criação automática do card
- [x] Verificar que card de correção mantém configurações do card original
- [x] Testar fluxo completo: executar teste → falha → criar card → visualizar no board

---

## 5. Considerações

### Riscos
- **Performance:** Criação de muitos cards de correção pode impactar performance
  - Mitigação: Limitar a 1 card de correção por card original ativo

- **Duplicação:** Múltiplas execuções de teste podem criar cards duplicados
  - Mitigação: Verificar se já existe card de correção não resolvido antes de criar novo

### Dependências
- Migration do banco de dados deve ser executada antes do deploy
- Frontend e backend devem ser atualizados simultaneamente

### Melhorias Futuras
- Adicionar opção para desabilitar criação automática de cards
- Implementar agrupamento de múltiplos erros em um único card
- Adicionar sugestões de correção baseadas em IA