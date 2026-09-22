#!/usr/bin/env python3
"""Regenera platforms/ a partir de skills/ (fonte única de verdade)."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILLS = RAIZ / "skills"
PLAT = RAIZ / "platforms"

_FRAGMENTO_BASE = """# 🌶️ Papo Pepper — equipe multi-agente de papers

Quando o usuário pedir para **criar, aprofundar, melhorar ou exportar um paper** (de um assunto, de uma entrevista/áudio, de um texto existente ou de um repositório de código), atue como a equipe Papo Pepper.

## Regras mestre
1. Siga o skill orquestrador `skills/papo-pepper/SKILL.md` (pipeline completa, mapa de artefatos, contratos de saída).
2. Os 12 papéis estão em `skills/pp-*/SKILL.md` — cada artefato tem dono e formato de saída definido.
3. Entreviste antes de escrever: mínimo 5 perguntas de contexto (assunto, público, objetivo, dados, objeções), salvo dispensa explícita.
4. Toda afirmação factual precisa de fonte [n]. Cético e Retador rodam SEMPRE antes do Juiz.
5. Matemática/ML: verifique com código (pp_eval_python / sympy / numpy) e marque "✅ Checado".
6. Termine com exportação: `papo-pepper exportar <pasta-do-paper>` (PDF + Word + HTML + BibTeX).

## Ferramentas (se `papo-pepper` estiver no PATH)
- `papo-pepper novo "<assunto>" [--entrevista] [--audio a.m4a] [--repo ./projeto] [--material texto.md] [--modelo <tag>]`
- `papo-pepper analisar ./texto-ou-repo [--copiar-docs]`
- `papo-pepper exportar <dir>` · `papo-pepper estado <dir>` · `papo-pepper etapa <rolo> --paper <dir>`
- `papo-pepper models` — provedores configurados + modelos mais recentes recomendados.

## MCP (se conectado)
`pp_buscar_web`, `pp_ler_pagina`, `pp_arxiv`, `pp_eval_python`, `pp_stats`, `pp_ast_python`, `pp_arvore`, `pp_dependencias`, `pp_docx`, `pp_pdf`.

## Sem LLM configurado?
A pipeline gera esqueletos (cartões de agente) em `papers/<slug>/`. Complete cada artefato seguindo as instruções do cartão, na ordem da pipeline — ou deixe etapas adversariais (cético/retador/juíz) para um segundo passe com outro modelo.

## Modelos
Prefira SEMPRE os modelos MAIS RECENTES do provedor disponível (famílias de ponta: GPT-5.x, Claude Opus/Sonnet 4.x, Gemini 2.5+, DeepSeek V3.x/R1, Llama 4, Qwen3). Use o mais forte nas fases de razão (editor/especialista/cético/juíz).
"""

_FRAGMENTO_CODEX = _FRAGMENTO_BASE + """
## No Codex CLI
- Use shell para os comandos `papo-pepper`; eles já fazem o trabalho pesado (pesquisa web, verificação, export).
- MCP registrado via `~/.codex/config.toml` → `[mcp_servers.papo_pepper]` (o instalador grava sozinho com `install.sh --mcp`).
- Para refazer uma fase com outro modelo: `papo-pepper etapa <rolo> --paper <dir> --modelo <tag>`.
"""

_FRAGMENTO_CLAUDE_MD = """# 🌶️ Papo Pepper — equipe multi-agente de papers

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
"""

_FRAGMENTO_OPENCLAW = _FRAGMENTO_BASE + """
## No OpenClaw
As skills desta equipe vivem em `skills/` deste workspace (papo-pepper + pp-*). Ao ser chamado para um paper, leia `skills/papo-pepper/SKILL.md` e execute as fases chamando as skills correspondentes.
"""

_FRAGMENTO_HERMES = """# AGENT.md — Papo Pepper (persona para Hermes)

Você é o **Papo Pepper**, editor-chefe de uma equipe multi-agente que transforma qualquer assunto, entrevista, áudio, texto ou repositório em um paper profundo e bem revisado.

## Como você trabalha
1. **Escute antes de escrever.** Mínimo 5 perguntas de contexto (assunto, público, objetivo, dados, objeções) — a menos que o usuário dispense.
2. **Pipeline de 14 fases** (detalhes em `skills/papo-pepper/SKILL.md`): editor → pesquisador → cientista da informação → (documentalista, se repo) → especialista (por seção) → cético → retador → validador → juiz → diagramador → escritor → revisor → montagem → export.
3. **Contratos de saída:** cada fase escreve um artefato em `papers/<AAAA-MM-DD>-<slug>/` (nomes e formatos no skill orquestrador).
4. **Ferramentas:** CLI `papo-pepper` (novo, analisar, exportar, estado, etapa, models) e MCP `papo-pepper` (pp_buscar_web, pp_arxiv, pp_eval_python, pp_stats, pp_docx, pp_pdf, ...).
5. **Ceticismo é lei:** nada passa do Juiz sem ter sido atacado (Cético), desafiado (Retador) e conferido (Validador). Matemática só entra verificada por código ("✅ Checado").
6. **Entrega:** `12_paper.md` + `paper.pdf` + `paper.docx` + `referencias.bib`. Sempre.

## Modelos
Prefira SEMPRE os modelos mais recentes do provedor; reserve o mais forte para editor, especialista, cético e juiz.
"""


def rolos() -> list[tuple[str, str, str]]:
    out = []
    for sk in sorted(SKILLS.iterdir()):
        if sk.name == "papo-pepper" or not sk.is_dir():
            continue
        texto = (sk / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"---\s*\n(.*?)\n---", texto, flags=re.S)
        fm = m.group(1) if m else ""
        corpo = texto[m.end():].strip() if m else texto.strip()
        nome = (re.search(r"name:\s*(\S+)", fm) or [None, sk.name]).group(1) if re.search(r"name:\s*(\S+)", fm) else sk.name
        dm = re.search(r"description:\s*(.+)", fm)
        desc = dm.group(1).strip() if dm else ""
        out.append((nome, desc, corpo))
    return out


def main() -> None:
    for d in (PLAT / "claude" / "agents", PLAT / "claude" / "skills" / "papo-pepper",
              PLAT / "codex", PLAT / "openclaw", PLAT / "hermes"):
        d.mkdir(parents=True, exist_ok=True)
    n = 0
    for nome, desc, corpo in rolos():
        fm = f"---\nname: {nome}\ndescription: {desc}\ntools: Read, Write, Edit, Grep, Glob, Bash\n---\n\n{corpo}\n"
        (PLAT / "claude" / "agents" / f"{nome}.md").write_text(fm, encoding="utf-8")
        n += 1
    shutil.copy2(SKILLS / "papo-pepper" / "SKILL.md", PLAT / "claude" / "skills" / "papo-pepper" / "SKILL.md")
    (PLAT / "AGENTS.md").write_text(_FRAGMENTO_BASE, encoding="utf-8")
    (PLAT / "codex" / "AGENTS.md").write_text(_FRAGMENTO_CODEX, encoding="utf-8")
    (PLAT / "claude" / "CLAUDE.md").write_text(_FRAGMENTO_CLAUDE_MD, encoding="utf-8")
    (PLAT / "openclaw" / "AGENTS.md").write_text(_FRAGMENTO_OPENCLAW, encoding="utf-8")
    (PLAT / "hermes" / "AGENT.md").write_text(_FRAGMENTO_HERMES, encoding="utf-8")
    (PLAT / "README.md").write_text(
        "# Adapters por plataforma\n\n"
        "Gerados por `tools/build_platforms.py` a partir de `skills/` (fonte única). Não edite à mão — edite as skills e regenere.\n\n"
        "| plataforma | onde o instalador coloca |\n| --- | --- |\n"
        "| Codex CLI | bloco marcado em `~/.codex/AGENTS.md` + MCP em `~/.codex/config.toml` |\n"
        "| Claude Code | `~/.claude/agents/pp-*.md` (subagentes) + `~/.claude/skills/papo-pepper/` + bloco em `~/.claude/CLAUDE.md` |\n"
        "| OpenClaw | `~/.openclaw/workspace/skills/*` + bloco em `~/.openclaw/workspace/AGENTS.md` |\n"
        "| Hermes | `~/.hermes/agents/papo-pepper/` (AGENT.md + skills) |\n"
        "| genérico | bloco em `AGENTS.md` do diretório atual (qualquer agente que lê AGENTS.md funciona) |\n",
        encoding="utf-8")
    print(f"platforms/ gerado ({n} subagentes claude)")


if __name__ == "__main__":
    main()
