# Recomendações de Testes - Auto-Limpeza de Cards

**Documento:** Guia prático para testar a feature de auto-limpeza
**Data:** 10 de Janeiro de 2025
**Nível de Urgência:** 🟡 Médio (implementação OK, testes pending)

---

## 📋 Checklist Rápido (5 minutos)

Execute este smoke test para verificação rápida:

```bash
# 1. Reiniciar backend
cd backend && python -m src.main &

# 2. Esperar 2 segundos
sleep 2

# 3. Testar API
curl -s http://localhost:3001/api/settings/auto-cleanup | jq .

# 4. Abrir navegador
open http://localhost:5173

# 5. Verificações visuais
# - [ ] Coluna "Completed" existe?
# - [ ] SettingsPage carrega?
# - [ ] Consegue mover card para Done?
```

---

## 🧪 Testes Manuais (30-45 minutos)

### Teste 1: Verificação da Coluna

**Objetivo:** Confirmar que a coluna "Completed" existe e funciona

```
1. Navegue para http://localhost:5173
2. Na tela de Kanban, procure pelas colunas
3. ESPERADO: Você deve ver "Completed" entre "Done" e "Archived"
4. VERIFICAR: A coluna está vazia inicialmente
5. SCREENSHOT: Tire screenshot da coluna em repouso
```

### Teste 2: Collapsible Functionality

**Objetivo:** Verificar se a coluna pode ser colapsada

```
1. Clique no header da coluna "Completed"
2. ESPERADO: Coluna colapsa, mostrando ▶ no header
3. Clique novamente
4. ESPERADO: Coluna expande, mostrando ▼ no header
5. Verifique que os cards aparecem quando expandida
6. SCREENSHOT: Capture estado collapsed e expanded
```

### Teste 3: Settings Page - Carregamento

**Objetivo:** Confirmar que a Settings page carrega e mostra auto-cleanup section

```
1. Navegue para a Settings page (ícone de engrenagem ou /settings)
2. ESPERADO: Página carrega sem erros
3. Procure por seção "Auto-limpeza de Cards Concluídos"
4. VERIFICAR elementos:
   - [ ] Checkbox "Mover automaticamente cards de Done para Completed"
   - [ ] Input numérico com rótulo "Mover após X dias"
   - [ ] Info box com explicação sobre coluna Completed
5. SCREENSHOT: Capture a seção de auto-cleanup
```

### Teste 4: Settings - Toggle Enable/Disable

**Objetivo:** Testar se o toggle de enable/disable funciona

```
1. Na Settings page, localize o checkbox de auto-cleanup
2. Se está marcado, desmarque (será desabilitado)
3. ESPERADO: Checkbox mostra estado unchecked
4. Atualize a página (F5)
5. ESPERADO: Checkbox continua desmarcado
6. Marque novamente
7. ESPERADO: Checkbox mostra estado checked
8. Atualize
9. ESPERADO: Checkbox continua marcado
```

### Teste 5: Settings - Alterar Dias

**Objetivo:** Testar se a alteração de dias funciona

```
1. Localize o input número "Mover após X dias"
2. Valor atual deve ser 7
3. Mude para 3
4. ESPERADO: Campo mostra "3"
5. Atualize página
6. ESPERADO: Campo ainda mostra "3"
7. Tente valores inválidos:
   - Digite 0 → ESPERADO: Rejeita ou mostra erro
   - Digite 31 → ESPERADO: Rejeita ou mostra erro
8. Volte para valor válido (7)
```

### Teste 6: Movimento de Cards - Done

**Objetivo:** Verificar se cards podem ser movidos para Done

```
1. Na coluna "Backlog" ou "Plan", pegue um card
2. Arraste para coluna "Done"
3. ESPERADO: Card aparece em Done
4. SCREENSHOT: Capture card em Done
5. Atualize página
6. ESPERADO: Card continua em Done
```

### Teste 7: Movimento de Cards - Completed

**Objetivo:** Verificar se cards podem ser movidos manualmente para Completed

```
1. Pegue um card que está em "Done"
2. Arraste para "Completed"
3. ESPERADO: Card desaparece de Done e aparece em Completed
4. Atualize página
5. ESPERADO: Card continua em Completed
6. SCREENSHOT: Capture card em Completed
```

### Teste 8: Verificar Timestamp (Dev Tools)

**Objetivo:** Verificar se o campo completed_at é setado corretamente

```
1. Abra DevTools (F12)
2. Vá para Application/Storage → Local Storage (ou use Network tab)
3. Mova um card NOVO para Done
4. Usando API cliente ou inspecionando, verifique:
   - ESPERADO: Campo completed_at está setado
   - ESPERADO: Valor é um timestamp ISO (2025-01-10T16:28:00Z)
5. Verifique que cards já existentes em Done também têm timestamp
```

### Teste 9: API Testing com curl

**Objetivo:** Testar endpoints da API diretamente

```bash
# 1. GET settings
curl -s http://localhost:3001/api/settings/auto-cleanup | jq .
# ESPERADO:
# {
#   "success": true,
#   "settings": {
#     "enabled": true,
#     "cleanup_after_days": 7
#   }
# }

# 2. PUT settings - disable
curl -X PUT http://localhost:3001/api/settings/auto-cleanup \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
# ESPERADO: success=true, enabled=false

# 3. PUT settings - change days
curl -X PUT http://localhost:3001/api/settings/auto-cleanup \
  -H "Content-Type: application/json" \
  -d '{"cleanup_after_days": 5}'
# ESPERADO: success=true, cleanup_after_days=5

# 4. PUT settings - invalid value
curl -X PUT http://localhost:3001/api/settings/auto-cleanup \
  -H "Content-Type: application/json" \
  -d '{"cleanup_after_days": 31}'
# ESPERADO: status 400 com mensagem de erro

# 5. Restore settings
curl -X PUT http://localhost:3001/api/settings/auto-cleanup \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "cleanup_after_days": 7}'
# ESPERADO: success=true com valores restaurados
```

---

## 🔧 Testes Técnicos (Para Desenvolvedores)

### Teste da Service de Auto-Cleanup

Se você tiver acesso ao código Python:

```python
# tests/test_auto_cleanup_service.py
import pytest
from datetime import datetime, timedelta
from backend.src.services.auto_cleanup_service import AutoCleanupService
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_cleanup_done_cards():
    """Test that old Done cards are moved to Completed."""
    # Setup
    mock_db = AsyncMock()
    service = AutoCleanupService(mock_db)

    # Simular cards antigos
    old_card = MagicMock()
    old_card.id = "card-1"
    old_card.column_id = "done"
    old_card.completed_at = datetime.utcnow() - timedelta(days=10)

    # Configurar mock para retornar cards antigos
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [old_card]
    mock_db.execute.return_value = mock_result

    # Execute
    moved_count = await service.cleanup_done_cards()

    # Assert
    assert moved_count == 1
    mock_db.execute.assert_called()
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_cleanup_respects_enabled_flag():
    """Test that cleanup respects enabled flag."""
    mock_db = AsyncMock()
    service = AutoCleanupService(mock_db)
    service.enabled = False

    moved_count = await service.cleanup_done_cards()

    assert moved_count == 0
    mock_db.execute.assert_not_called()
```

### Teste da API Settings

```python
# tests/test_settings_api.py
import pytest
from fastapi.testclient import TestClient
from backend.src.main import app

client = TestClient(app)

def test_get_auto_cleanup_settings():
    response = client.get("/api/settings/auto-cleanup")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "settings" in data
    assert data["settings"]["enabled"] in [True, False]
    assert 1 <= data["settings"]["cleanup_after_days"] <= 30

def test_update_auto_cleanup_settings():
    response = client.put(
        "/api/settings/auto-cleanup",
        json={"cleanup_after_days": 5}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["cleanup_after_days"] == 5

def test_reject_invalid_days():
    response = client.put(
        "/api/settings/auto-cleanup",
        json={"cleanup_after_days": 31}
    )
    assert response.status_code == 400

    response = client.put(
        "/api/settings/auto-cleanup",
        json={"cleanup_after_days": 0}
    )
    assert response.status_code == 400
```

---

## 📊 Matriz de Testes

| ID | Teste | Manual | Automatizado | Status | Notas |
|----|-------|--------|--------------|--------|-------|
| T1 | Coluna Completed existe | ✅ | ⏳ | Pending | Simple UI check |
| T2 | Coluna é colapsável | ✅ | ⏳ | Pending | Click behavior |
| T3 | Settings page carrega | ✅ | ⏳ | Pending | Route/component test |
| T4 | Toggle enable/disable | ✅ | ⏳ | Pending | State persistence |
| T5 | Alterar dias (1-30) | ✅ | ⏳ | Pending | Validation test |
| T6 | Rejeitar valores inválidos | ✅ | ⏳ | Pending | Boundary test |
| T7 | Move to Done | ✅ | ⏳ | Pending | Drag & drop |
| T8 | Move to Completed | ✅ | ⏳ | Pending | Drag & drop |
| T9 | Timestamp auto-set | ✅ | ⏳ | Pending | Data integrity |
| T10 | API GET settings | ✅ | ⏳ | Pending | HTTP test |
| T11 | API PUT settings | ✅ | ⏳ | Pending | HTTP test |
| T12 | API validation | ✅ | ⏳ | Pending | Error handling |

---

## 🎬 Ordem Recomendada de Execução

### Fase 1: Smoke Test (5 min)
1. Restart backend
2. Teste API com curl
3. Verificação visual rápida no navegador

### Fase 2: Testes Manuais (30-45 min)
1. Testes 1-9 em sequência
2. Capturar screenshots
3. Documentar qualquer comportamento inesperado

### Fase 3: Testes de API (10 min)
1. Executar todos os curl commands
2. Documentar respostas
3. Verificar códigos HTTP

### Fase 4: Testes Automatizados (1-2 horas)
1. Implementar testes unitários
2. Implementar testes de integração
3. Executar com pytest

---

## 🐛 Possíveis Problemas e Soluções

### Problema 1: "Cannot GET /api/settings/auto-cleanup"
```
Causa: Backend não foi reiniciado
Solução:
  $ Ctrl+C no backend
  $ cd backend && python -m src.main
  $ Aguarde "Uvicorn running..."
```

### Problema 2: Coluna "Completed" não aparece
```
Causa: Frontend não foi recarregado
Solução:
  $ Ctrl+F5 (hard refresh no navegador)
  $ Limpar cache: DevTools → Application → Clear Site Data
```

### Problema 3: Settings não persistem após refresh
```
Causa: Settings ainda estão em memória (não em DB)
Esperado no momento (recomendação futura: mover para DB)
Solução: Implementar persistência em database
```

### Problema 4: Erro 400 ao alterar dias
```
Causa: Valor fora do range 1-30
Solução: Usar valor válido entre 1 e 30
```

---

## 📝 Template para Documentar Testes

```markdown
## Teste [Número]: [Descrição]

**Data:** [Data]
**Testador:** [Nome]

### Passos
1. [Passo 1]
2. [Passo 2]
...

### Resultado
- [ ] Passo 1: ✅/❌
- [ ] Passo 2: ✅/❌

### Screenshots
- [Descrição]: ![Imagem](caminho)

### Observações
- [Observação 1]
- [Observação 2]

### Status Final
**PASSOU / FALHOU / PARCIAL**
```

---

## 🎯 Critérios de Sucesso

Para considerar a feature como **TESTADA E APROVADA**, todos os seguintes critérios devem ser atendidos:

✅ **UI/UX:**
- [ ] Coluna Completed é visível e acessível
- [ ] Coluna pode ser colapsada/expandida
- [ ] Styling está correto (matching Archived/Cancelado)
- [ ] Nenhum erro em DevTools console

✅ **Settings:**
- [ ] Settings page carrega sem erros
- [ ] Toggle enable/disable funciona
- [ ] Alterar dias funciona
- [ ] Valores inválidos são rejeitados
- [ ] Valores persistem após refresh (memória é OK por enquanto)

✅ **API:**
- [ ] GET /api/settings/auto-cleanup retorna 200
- [ ] PUT /api/settings/auto-cleanup funciona
- [ ] Validação de range (1-30) funciona
- [ ] Error handling funciona (status 400)

✅ **Data:**
- [ ] Cards podem ser movidos para Done
- [ ] Cards podem ser movidos para Completed
- [ ] completed_at timestamp é setado
- [ ] Dados persistem após refresh

---

## 🚀 Próximos Passos Após Validação

Se todos os testes passarem:

1. **Implementar testes automatizados** (opcional mas recomendado)
2. **Iniciar AutoCleanupService** no lifespan da app
3. **Mover settings para database** (em vez de em memória)
4. **Considerar persistência** de configurações por workspace
5. **Adicionar monitoramento** (logging/alerting de cleanups)

---

## 📞 Contato/Suporte

Para dúvidas ou problemas durante os testes:

1. Consulte o spec original: `specs/auto-limpeza-cards-done.md`
2. Verifique o relatório de validação: `IMPLEMENTATION_VALIDATION_REPORT.md`
3. Veja os relatórios detalhados: `test-reports/playwright/2026-01-10_16-23-39/`

---

**Documento gerado:** 10 de Janeiro de 2025
**Versão:** 1.0
