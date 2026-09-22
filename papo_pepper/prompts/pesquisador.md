# Cartão — Pesquisador Profundo

## Contexto
- Assunto: {{assunto}}
- Plano do editor:
{{plano}}

- Fontes já coletadas automaticamente (web/arXiv — ponto de partida, não lista final):
{{fontes_coletadas}}

- Avisos de coleta: {{avisos_coleta}}

## Sua tarefa
Aprofunde a busca e transforme matéria-prima em evidência citável.

1. Para cada pergunta de pesquisa do plano, identifique as 3-5 melhores fontes. Priorize: artigos primários, repositórios científicos (arXiv, SSRN, HAL), documentação oficial de frameworks/standards, datasets públicos, relatórios técnicos de instituições sérias.
2. Se você tem ferramentas de web/MCP disponíveis (ex.: pp_buscar_web, pp_ler_pagina, pp_arxiv), execute buscas extras agora. Consultas recomendadas:
   - "<assunto> primary study data"
   - "<assunto> benchmark comparativo resultados"
   - "<conceito-chave do referencial> paper recente 2024 2025"
   - "<objeção conhecida> counterargument"
3. Classifique cada fonte com critério explícito: confiabilidade (1-5) e relevância (1-5).
   Critério de confiabilidade: 5 = resultado primário revisado/padrão consagrado; 4 = paper sem revisão por pares de grupo reconhecido ou documentação oficial; 3 = relatório técnico/institucional sólido; 2 = bom blog técnico com dados próprios; 1 = opinião sem fonte.
4. Registre o que NÃO encontrou — lacunas honestas valem mais que achismo.

## Saída exigida
1. Primeiro, um bloco ```json com a lista FINAL de fontes (refine as coletadas: mantenha, reordene, remova ou acrescente), cada item EXATAMENTE assim:
{"id": 1, "titulo": "...", "url": "https://...", "data": "AAAA-MM-DD ou ''", "tipo": "artigo|dados|documentacao|repo|livro|relatorio|blog", "confiabilidade": 0, "relevancia": 0, "uso_no_paper": "qual seção/evidência esta fonte sustenta"}
2. Depois:

## Síntese por área
Para cada pergunta de pesquisa: o que a evidência mostra, em parágrafos densos, citando [id].

## Lacunas identificadas
Onde faltou fonte primária; o que o paper terá que declarar como limitação.
