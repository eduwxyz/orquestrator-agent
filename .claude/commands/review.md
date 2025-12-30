---
description: Revisa a implementacao comparando com a spec original. Verifica se faz sentido, se faltou algo, e se segue os padroes definidos.
argument-hint: [caminho/para/spec.md]
model: opus
---

**Nota:** O modelo Claude usado para este comando pode ser configurado por card na UI. O padrão é Opus 4.5.

# Review Implementation

Revise a implementacao do plano especificado em: $ARGUMENTS

## Proposito

Este comando faz uma revisao critica e detalhada comparando o que foi planejado na spec com o que foi efetivamente implementado. O objetivo e identificar:

- Itens faltantes ou incompletos
- Divergencias entre spec e implementacao
- Problemas de arquitetura ou padrao
- Oportunidades de melhoria
- Potenciais bugs ou inconsistencias

## Instrucoes

1. Se `$ARGUMENTS` estiver vazio, liste os arquivos disponiveis em `specs/` e pergunte qual revisar
2. Leia o arquivo de spec completo
3. Execute todas as fases de revisao abaixo
4. Gere um relatorio detalhado de revisao

## Fases de Revisao

### Fase 1: Inventario de Arquivos

1. Extraia a lista de arquivos da secao "Arquivos a Serem Criados/Modificados" da spec
2. Para cada arquivo:
   - Verifique se existe
   - Leia o conteudo completo
   - Compare estrutura e conteudo com o que foi especificado
3. Identifique:
   - Arquivos especificados mas nao criados
   - Arquivos criados mas nao especificados (extras)
   - Arquivos com implementacao divergente

### Fase 2: Analise de Aderencia a Spec

Para cada arquivo implementado, compare com os "Detalhes Tecnicos" da spec:

1. **Estrutura do Codigo:**
   - Classes/funcoes esperadas estao presentes?
   - Assinaturas de metodos conferem?
   - Tipos e validacoes estao corretos?

2. **Logica de Negocio:**
   - A implementacao segue a logica descrita na spec?
   - Ha divergencias no comportamento esperado?
   - Casos de borda foram tratados conforme especificado?

3. **Padroes e Convencoes:**
   - Nomenclatura segue o padrao definido?
   - Arquitetura em camadas esta sendo respeitada?
   - Imports e dependencias estao corretos?

### Fase 3: Verificacao de Objetivos

1. Releia a secao "Objetivos" da spec
2. Para cada objetivo listado:
   - Verifique se foi completamente atendido
   - Identifique implementacoes parciais
   - Avalie se a abordagem faz sentido

3. Classifique cada objetivo:
   - Completo: Totalmente implementado conforme spec
   - Parcial: Implementado mas com lacunas
   - Divergente: Implementado de forma diferente
   - Ausente: Nao implementado

### Fase 4: Revisao de Qualidade

Analise criticamente a implementacao:

1. **Consistencia:**
   - O codigo e consistente internamente?
   - Os padroes sao aplicados uniformemente?
   - Ha duplicacao de logica?

2. **Robustez:**
   - Erros sao tratados adequadamente?
   - Validacoes estao presentes onde necessario?
   - Ha potenciais pontos de falha?

3. **Legibilidade:**
   - O codigo e claro e compreensivel?
   - Nomes de variaveis/funcoes sao descritivos?
   - Ha complexidade desnecessaria?

4. **Decisoes Arquiteturais:**
   - As decisoes da spec foram seguidas?
   - Ha decisoes que divergem sem justificativa?
   - A arquitetura escolhida faz sentido para o problema?

### Fase 5: Verificacao de Testes

Se a spec inclui secao de "Testes":

1. Verifique se os testes especificados existem
2. Analise se cobrem os cenarios descritos
3. Identifique testes faltantes
4. Avalie qualidade dos testes implementados

## Formato do Relatorio

Gere um relatorio estruturado:

```markdown
# Revisao: [nome-da-spec]

## Resumo Executivo

| Aspecto | Status | Observacao |
|---------|--------|------------|
| Arquivos | X/Y implementados | [breve nota] |
| Objetivos | X/Y atendidos | [breve nota] |
| Aderencia a Spec | Alta/Media/Baixa | [breve nota] |
| Qualidade Geral | Boa/Regular/Ruim | [breve nota] |

## Analise Detalhada

### Arquivos

#### Implementados Conforme Spec
- `arquivo1.py` - OK
- `arquivo2.py` - OK

#### Com Divergencias
- `arquivo3.py`
  - **Esperado:** [descricao da spec]
  - **Implementado:** [descricao do que foi feito]
  - **Impacto:** [avaliacao do impacto]

#### Faltantes
- `arquivo4.py` - [motivo/impacto]

### Objetivos

#### Atendidos
- [x] Objetivo 1 - Implementado corretamente

#### Parcialmente Atendidos
- [ ] Objetivo 2
  - **Faltando:** [o que falta]
  - **Recomendacao:** [como completar]

#### Nao Atendidos
- [ ] Objetivo 3
  - **Motivo:** [por que nao foi atendido]
  - **Recomendacao:** [como implementar]

### Problemas Encontrados

#### Criticos (devem ser corrigidos)
1. **[Titulo do Problema]**
   - Localizacao: `arquivo:linha`
   - Descricao: [o que esta errado]
   - Impacto: [consequencia do problema]
   - Sugestao: [como corrigir]

#### Importantes (deveriam ser corrigidos)
1. ...

#### Menores (podem ser melhorados)
1. ...

### Divergencias da Spec

| Item | Spec | Implementacao | Avaliacao |
|------|------|---------------|-----------|
| [item] | [esperado] | [feito] | [se faz sentido] |

### Pontos Positivos

- [aspectos bem implementados]
- [boas decisoes tomadas]
- [melhorias alem da spec que agregam valor]

## Recomendacoes

### Correcoes Necessarias
1. [acao especifica com arquivo/linha]
2. ...

### Melhorias Sugeridas
1. [sugestao de melhoria]
2. ...

### Proximos Passos
1. [acao recomendada]
2. ...

## Conclusao

**Veredito:** [APROVADO / APROVADO COM RESSALVAS / REPROVADO]

[Resumo final com justificativa do veredito]
```

## Regras

- **Sempre** leia a spec original E os arquivos implementados antes de revisar
- **Sempre** seja critico mas construtivo nas observacoes
- **Nunca** modifique arquivos durante a revisao (apenas leitura e analise)
- **Compare** detalhadamente spec vs implementacao, nao apenas checkboxes
- **Avalie** se divergencias fazem sentido ou sao problemas
- **Sugira** correcoes especificas com localizacao no codigo
- **Reconheca** pontos positivos e boas decisoes

## Diferenca para /test-implementation

- `/test-implementation`: Foca em executar testes e verificar se o codigo funciona
- `/review`: Foca em revisar se a implementacao esta alinhada com a spec e se faz sentido

O `/review` e uma analise mais profunda e critica, enquanto `/test-implementation` e uma validacao tecnica de funcionamento.

## Exemplo de Uso

```
/review specs/feature-auth.md
```

O comando ira:
1. Ler a spec completa de `specs/feature-auth.md`
2. Identificar todos os arquivos que deveriam existir
3. Ler e analisar cada arquivo implementado
4. Comparar implementacao com os detalhes tecnicos da spec
5. Verificar se objetivos foram atendidos
6. Identificar problemas, divergencias e lacunas
7. Gerar relatorio completo de revisao com recomendacoes
