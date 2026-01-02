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
3. Execute todas as fases de validação abaixo
4. Gere um relatório final de qualidade

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
3. Executar a suíte de testes
4. Rodar lint e type check
5. Gerar relatório completo de validação
