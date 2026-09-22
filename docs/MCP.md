# Servidor MCP do Papo Pepper

Stdio, JSON-RPC 2.0, **zero dependências obrigatórias** (stdlib + httpx quando presente).
Comando: `python -m papo_pepper.mcp_server`

## Ferramentas

| Ferramenta | Argumentos | O que faz |
| --- | --- | --- |
| `pp_buscar_web` | query, limite | Busca DuckDuckGo HTML sem chave de API → títulos, URLs, trechos |
| `pp_ler_pagina` | url | Extrai texto limpo da página |
| `pp_arxiv` | query, limite | Papers do arXiv (título, autores, abstract, data) |
| `pp_eval_python` | code, timeout_s | Executa Python isolado — matemática, ML, checagens; matplotlib desenha (salve com `plt.savefig`) |
| `pp_stats` | amostra, amostra_b, operacoes | média/mediana/dp/min/max/q1/q3/iqr + correlação de Pearson + regressão linear (stdlib) |
| `pp_ast_python` | caminho | Funções/classes/docstrings de um projeto Python |
| `pp_arvore` | caminho, maximo | Árvore do projeto respeitando ignores comuns |
| `pp_dependencias` | caminho | Deps de pyproject/package.json/go.mod/Cargo.toml/requirements |
| `pp_docx` | markdown, saida, titulo, autor | Markdown → .docx profissional (usa o pacote instalado) |
| `pp_pdf` | markdown, saida, titulo | Markdown → .pdf (weasyprint → reportlab → fpdf2) |

## Conectando

**Claude Code:**
```bash
claude mcp add --scope user papo-pepper -- python -m papo_pepper.mcp_server
```

**Codex CLI** — em `~/.codex/config.toml` (o instalador `--mcp` já faz):
```toml
[mcp_servers.papo_pepper]
command = "python"
args = ["-m", "papo_pepper.mcp_server"]
```

**Qualquer host MCP (config JSON estilo Claude Desktop / OpenClaw):**
```json
{
  "mcpServers": {
    "papo-pepper": {
      "command": "python",
      "args": ["-m", "papo_pepper.mcp_server"]
    }
  }
}
```

> Dentro de uma pipeline, o Pesquisador usa `pp_buscar_web`/`pp_arxiv`; o Especialista e o
> Validador usam `pp_eval_python`/`pp_stats`; o Documentalista usa `pp_ast_python`/`pp_arvore`/`pp_dependencias`.
