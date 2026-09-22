# 🌶️ Papo Pepper — equipe multi-agente de papers

Quando pedirem um paper (assunto, entrevista, áudio, texto existente ou repositório), siga o skill `papo-pepper` (instalado em `.claude/skills/papo-pepper`). Pipeline de 14 fases; artefatos em `papers/<AAAA-MM-DD>-<slug>/`.

## Delegue aos subagentes (já instalados)
`pp-editor`, `pp-pesquisador`, `pp-cientista`, `pp-documentalista`, `pp-especialista`, `pp-cetico`, `pp-retador`, `pp-validador`, `pp-juiz`, `pp-diagramador`, `pp-escritor`, `pp-revisor` — um Task por fase, NA ORDEM da pipeline. Cada subagente sabe seu contrato de saída (veja `skills/pp-*/SKILL.md`).

## Regras inegociáveis
1. Entreviste antes de escrever (≥5 perguntas de contexto), salvo dispensa.
2. Toda afirmação factual tem [n]; fontes vêm de `pp_buscar_web`/`pp_arxiv`/web + refinamento do pesquisador.
3. Cético + Retador + Validador SEMPRE antes do Juiz; veredito REVISAR ⇒ Escritor incorpora e responde todos os desafios do ranking.
4. Matemática/ML verificada por `pp_eval_python` (sympy/numpy) com marca "✅ Checado".
5. Exporte ao final: `papo-pepper exportar <dir>` (PDF/Word/HTML/BibTeX).

## Ferramentas
CLI `papo-pepper` (novo, analisar, exportar, estado, etapa, models) + MCP `papo-pepper` (10 ferramentas). `papo-pepper models` mostra os modelos mais recentes recomendados — prefira sempre o mais recente do provedor.
