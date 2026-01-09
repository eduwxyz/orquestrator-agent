---
description: Valida e testa o que foi implementado pelo comando /implement. Verifica arquivos, executa testes e gera relatório.
argument-hint: [caminho/para/spec.md]
model: haiku
---

**Nota:** O modelo Claude usado para este comando pode ser configurado por card na UI. O padrão é Opus 4.5.

# Test Implementation

Valide a implementação do plano especificado em: $ARGUMENTS

## Instruções

1. Se `$ARGUMENTS` estiver vazio, liste os arquivos disponíveis em `specs/` e pergunte qual validar
2. Leia o arquivo de plano especificado
3. Execute todas as fases de validação abaixo (Fases 1-6)
4. A Fase 6 (Browser Validation) é condicional - apenas execute se a implementação envolver frontend
5. Gere um relatório final de qualidade consolidando todas as fases

## Fases de Validação

### Fase 1: Verificação de Arquivos

1. Extraia a lista de arquivos da seção "Arquivos a Serem Modificados/Criados" do plano
2. Para cada arquivo listado:
   - **Se ação era "Criar"**: Verifique se o arquivo existe
   - **Se ação era "Modificar"**: Verifique se o arquivo foi modificado (use `git diff` se disponível)
3. Registre status de cada arquivo:
   - ✅ Arquivo criado/modificado conforme esperado
   - ❌ Arquivo ausente ou não modificado
   - ⚠️ Arquivo existe mas conteúdo diverge do esperado

### Fase 2: Verificação de Checkboxes

1. Leia o arquivo de plano novamente
2. Extraia todos os checkboxes (`- [ ]` e `- [x]`)
3. Calcule a taxa de conclusão:
   - Total de checkboxes
   - Checkboxes marcados como concluídos
   - Checkboxes pendentes
4. Liste quais itens ainda estão pendentes (se houver)

### Fase 3: Execução de Testes

1. Identifique a seção "Testes" no plano
2. Para cada teste listado:

   **Testes Unitários:**
   ```bash
   # Detecte o runner de testes do projeto
   # npm test, pytest, go test, cargo test, etc.
   ```

   **Testes de Integração:**
   ```bash
   # Execute testes de integração se configurados
   ```

3. Capture resultados:
   - ✅ Testes passando
   - ❌ Testes falhando (inclua mensagem de erro)
   - ⏭️ Testes pulados/não encontrados

### Fase 4: Análise de Qualidade

1. **Lint/Formatação**: Execute linter do projeto se disponível
   ```bash
   # eslint, prettier, black, golint, etc.
   ```

2. **Type Check**: Execute verificação de tipos se aplicável
   ```bash
   # tsc --noEmit, mypy, etc.
   ```

3. **Build**: Tente compilar/buildar o projeto
   ```bash
   # npm run build, cargo build, go build, etc.
   ```

### Fase 5: Cobertura de Código (Opcional)

Se o projeto tiver cobertura configurada:
```bash
# npm run test:coverage, pytest --cov, etc.
```

Analise:
- Cobertura geral do projeto
- Cobertura dos arquivos novos/modificados
- Áreas sem cobertura de teste

### Fase 6: Browser Validation (Web Testing)

**Objetivo**: Validar a implementação visualmente no browser usando automação Playwright.

**Quando executar**: Esta fase deve ser executada para implementações que envolvem UI web (frontend).

**Como executar**:

1. **Verificar se é necessário**:
   - Se o plano envolve mudanças no frontend (arquivos em `frontend/`, componentes React, etc.), execute esta fase
   - Se é apenas backend ou configuração, pule esta fase

2. **Verificar servidores**:
   ```bash
   # Verificar se frontend está rodando
   curl -s http://localhost:5173 > /dev/null && echo "Frontend OK" || echo "Frontend DOWN"

   # Verificar se backend está rodando
   curl -s http://localhost:3001 > /dev/null && echo "Backend OK" || echo "Backend DOWN"
   ```

   - Se servidores NÃO estão rodando: Informe o usuário e instrua a subir com `npm run dev`
   - Se servidores estão rodando: Prossiga para o próximo passo

3. **Invocar playwright-agent**:
   Use o Task tool para invocar o playwright-agent:
   ```
   Task tool with subagent_type='playwright-agent':
   "Validate the implementation from [caminho-do-spec]. Test acceptance criteria and generate browser validation report."
   ```

4. **Aguardar resultado**:
   - O playwright-agent irá retornar exit code 0 (sucesso) ou 1 (falha)
   - Capturar localização do relatório gerado em `./test-reports/playwright/`
   - Incluir resultado no relatório final

5. **Registre resultados**:
   - ✅ Browser tests passando - todos os acceptance criteria validados
   - ⚠️ Browser tests com ressalvas - alguns critérios passaram, outros falharam
   - ❌ Browser tests falhando - erro crítico ou maioria dos critérios falharam
   - ⏭️ Browser tests pulados - servidores não estavam rodando ou não aplicável

**Nota**: Esta fase é automatizada mas requer que os servidores estejam rodando. Se você é invocado via kanban, os servidores provavelmente já estão up.

## Formato do Relatório Final

Gere um relatório estruturado:

```markdown
# Relatório de Validação: [nome-do-plano]

## Resumo Executivo
| Métrica | Status |
|---------|--------|
| Arquivos | X/Y criados/modificados |
| Checkboxes | X/Y concluídos |
| Testes | X passando, Y falhando |
| Build | ✅/❌ |
| Lint | ✅/❌ |
| Browser Tests | ✅/⚠️/❌/⏭️ |

## Detalhes

### Arquivos Verificados
- ✅ `src/arquivo1.ts` - Criado conforme plano
- ✅ `src/arquivo2.ts` - Modificado conforme plano
- ❌ `src/arquivo3.ts` - Não encontrado

### Checkboxes Pendentes
- [ ] Item X ainda não concluído
- [ ] Item Y ainda não concluído

### Resultados dos Testes
```
[output dos testes]
```

### Browser Validation (Fase 6)
**Status**: ✅/⚠️/❌/⏭️

**Relatório Playwright**: `test-reports/playwright/YYYY-MM-DD_HH-MM-SS/playwright-report.md`

**Acceptance Criteria Validados**:
- ✅ Critério 1: [descrição]
- ✅ Critério 2: [descrição]
- ❌ Critério 3: [descrição] - [razão da falha]

**Screenshots Capturados**: [número] screenshots salvos no diretório do relatório

**Observações**:
- [Quaisquer observações relevantes do teste browser]
- [Problemas de UI encontrados]
- [Comportamentos inesperados]

**Nota**: Se esta seção estiver marcada como ⏭️ (pulada), significa que:
- Servidores não estavam rodando, OU
- A implementação não envolve mudanças de frontend

### Problemas Encontrados
1. Descrição do problema 1
2. Descrição do problema 2

### Recomendações
1. Ação recomendada 1
2. Ação recomendada 2

## Conclusão
[Status geral: APROVADO / APROVADO COM RESSALVAS / REPROVADO]
```

## Regras

- **Sempre** leia o plano original antes de validar
- **Sempre** execute todos os testes disponíveis
- **Nunca** modifique arquivos durante a validação (apenas leitura)
- **Reporte** todos os problemas encontrados, mesmo menores
- **Sugira** correções para problemas identificados

## Detecção Automática de Ferramentas

Detecte automaticamente as ferramentas do projeto:

| Arquivo | Ferramenta de Teste | Comando |
|---------|---------------------|---------|
| `package.json` | npm/yarn | `npm test` |
| `pyproject.toml` | pytest | `pytest` |
| `Cargo.toml` | cargo | `cargo test` |
| `go.mod` | go | `go test ./...` |
| `Makefile` | make | `make test` |

## Exemplo de Uso

```
/test-implementation specs/feature-auth.md
```

O comando irá:
1. Verificar se todos os arquivos do plano existem
2. Conferir se checkboxes foram marcados
3. Executar a suíte de testes (unitários e integração)
4. Rodar lint e type check
5. Analisar cobertura de código (se disponível)
6. **Validar no browser usando Playwright** (se envolver frontend)
7. Gerar relatório completo de validação

**Nota sobre Fase 6 (Browser Testing)**:
- Requer servidores rodando (frontend:5173 e backend:3001)
- Apenas executada se a implementação envolve mudanças no frontend
- Gera screenshots e relatório detalhado com validação visual
- Integra resultados no relatório final
