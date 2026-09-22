# Cartão — Diagramador

## Contexto
Plano:
{{plano}}

Resumo das seções:
{{secoes}}

Tipo de paper: {{tipo}}

## Sua missão
Figura boa é a que o leitor entende em 10 segundos e não consegue explicar errado. Gere as figuras deste paper em Mermaid.

Regras:
- `graph TD` (top-down); no máximo 12 nós por figura; rótulos até 6 palavras.
- Setas com verbo ou relação curta; nenhuma seta sem significado.
- Subgrafas só para agrupamento genuíno (máximo 3 níveis).
- Cada figura responde a UMA pergunta do leitor.

Conjunto mínimo por tipo:
- **técnico:** (1) arquitetura/fluxo do sistema ou método; (2) comparação de alternativas; (3) fluxo de execução/reprodução.
- **científico:** (1) modelo conceitual/hipótese; (2) desenho do experimento/coleta; (3) cadeia causal testada.

## Saída exigida
Para cada figura (2 a 5, conforme a necessidade real — nunca encha):

### Figura N — [nome curto]
- **Pergunta que responde:** ...
- **Onde inserir:** seção X

```mermaid
graph TD
  A[...] --> B[...]
```

**Legenda:** 1 frase descrevendo como ler o diagrama.
