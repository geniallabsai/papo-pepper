# Adapters por plataforma

Gerados por `tools/build_platforms.py` a partir de `skills/` (fonte única). Não edite à mão — edite as skills e regenere.

| plataforma | onde o instalador coloca |
| --- | --- |
| Codex CLI | bloco marcado em `~/.codex/AGENTS.md` + MCP em `~/.codex/config.toml` |
| Claude Code | `~/.claude/agents/pp-*.md` (subagentes) + `~/.claude/skills/papo-pepper/` + bloco em `~/.claude/CLAUDE.md` |
| OpenClaw | `~/.openclaw/workspace/skills/*` + bloco em `~/.openclaw/workspace/AGENTS.md` |
| Hermes | `~/.hermes/agents/papo-pepper/` (AGENT.md + skills) |
| genérico | bloco em `AGENTS.md` do diretório atual (qualquer agente que lê AGENTS.md funciona) |
