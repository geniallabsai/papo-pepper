"""Servidor MCP do Papo Pepper — stdio, JSON-RPC 2.0, zero dependências obrigatórias.

Linha de comando:  python -m papo_pepper.mcp_server

Ferramentas: pp_buscar_web, pp_ler_pagina, pp_arxiv, pp_eval_python, pp_stats,
pp_ast_python, pp_arvore, pp_dependencias, pp_docx, pp_pdf.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__

FERRAMENTAS = [
    {"name": "pp_buscar_web",
     "description": "Busca na web (DuckDuckGo HTML, sem chave de API). Retorna títulos, URLs e trechos.",
     "inputSchema": {"type": "object",
                     "properties": {"query": {"type": "string"}, "limite": {"type": "integer", "default": 6}},
                     "required": ["query"]}},
    {"name": "pp_ler_pagina",
     "description": "Baixa uma URL e devolve o texto limpo da página.",
     "inputSchema": {"type": "object",
                     "properties": {"url": {"type": "string"}},
                     "required": ["url"]}},
    {"name": "pp_arxiv",
     "description": "Busca papers no arXiv (API oficial).",
     "inputSchema": {"type": "object",
                     "properties": {"query": {"type": "string"}, "limite": {"type": "integer", "default": 5}},
                     "required": ["query"]}},
    {"name": "pp_eval_python",
     "description": "Executa Python isolado (timeout) para matemática, ML e checagens numéricas. matplotlib funciona; salve gráficos com plt.savefig().",
     "inputSchema": {"type": "object",
                     "properties": {"code": {"type": "string"}, "timeout_s": {"type": "integer", "default": 60}},
                     "required": ["code"]}},
    {"name": "pp_stats",
     "description": "Estatísticas puras (média, mediana, dp, percentis, IQR; com 2 amostras: Pearson + regressão linear simples).",
     "inputSchema": {"type": "object",
                     "properties": {"amostra": {"type": "array", "items": {"type": "number"}},
                                    "amostra_b": {"type": "array", "items": {"type": "number"}},
                                    "operacoes": {"type": "array", "items": {"type": "string"}}},
                     "required": ["amostra"]}},
    {"name": "pp_ast_python",
     "description": "Escaneia funções/classes/docstrings num diretório Python (AST).",
     "inputSchema": {"type": "object",
                     "properties": {"caminho": {"type": "string", "default": "."}}}},
    {"name": "pp_arvore",
     "description": "Lista a árvore de um projeto (ignora .git, node_modules etc.).",
     "inputSchema": {"type": "object",
                     "properties": {"caminho": {"type": "string", "default": "."},
                                    "maximo": {"type": "integer", "default": 200}}}},
    {"name": "pp_dependencias",
     "description": "Extrai dependências de pyproject.toml, package.json, go.mod, Cargo.toml, requirements.txt.",
     "inputSchema": {"type": "object",
                     "properties": {"caminho": {"type": "string", "default": "."}}}},
    {"name": "pp_docx",
     "description": "Converte um arquivo Markdown em .docx profissional (capa, sumário, estilos).",
     "inputSchema": {"type": "object",
                     "properties": {"markdown": {"type": "string"}, "saida": {"type": "string"},
                                    "titulo": {"type": "string"}, "autor": {"type": "string"}},
                     "required": ["markdown"]}},
    {"name": "pp_pdf",
     "description": "Converte um arquivo Markdown em .pdf (weasyprint → reportlab → fpdf2).",
     "inputSchema": {"type": "object",
                     "properties": {"markdown": {"type": "string"}, "saida": {"type": "string"},
                                    "titulo": {"type": "string"}, "autor": {"type": "string"}},
                     "required": ["markdown"]}},
]


def _ok(texto: str) -> dict:
    return {"content": [{"type": "text", "text": texto}], "isError": False}


def _erro(texto: str) -> dict:
    return {"content": [{"type": "text", "text": texto}], "isError": True}


def _stats(args: dict) -> str:
    a = list(args.get("amostra") or [])
    b = args.get("amostra_b")
    ops = [str(o).lower() for o in (args.get("operacoes") or ["media", "mediana", "dp", "min", "max"])]
    if not a:
        return "amostra vazia"
    quadris = statistics.quantiles(a, n=4) if len(a) >= 4 else (min(a), min(a), max(a))

    def val(o: str):
        if o in ("media", "mean"):
            return statistics.fmean(a)
        if o == "mediana":
            return statistics.median(a)
        if o in ("dp", "std"):
            return statistics.pstdev(a)
        if o == "min":
            return min(a)
        if o == "max":
            return max(a)
        if o == "q1":
            return quadris[0]
        if o == "q3":
            return quadris[2]
        if o == "iqr":
            return quadris[2] - quadris[0]
        if o == "n":
            return len(a)
        return None

    linhas = []
    for o in ops:
        v = val(o)
        if v is not None:
            linhas.append(f"{o}: {round(v, 6) if isinstance(v, float) else v}")
    if b and len(b) == len(a) and len(a) >= 3:
        try:
            r = statistics.correlation(a, b)
            n = len(a)
            mx, my = statistics.fmean(a), statistics.fmean(b)
            sxy = sum((x - mx) * (y - my) for x, y in zip(a, b))
            sxx = sum((x - mx) ** 2 for x in a)
            slope = sxy / sxx if sxx else float("nan")
            intercept = my - slope * mx
            linhas.append(f"correlacao_pearson(a,b): {round(r, 6)}")
            linhas.append(f"regressao_linear: y = {round(intercept, 6)} + {round(slope, 6)}*x")
        except statistics.StatisticsError as e:
            linhas.append(f"correlacao: indetereminada ({e})")
    return "\n".join(linhas) or "nenhuma operação reconhecida"


def _ast(caminho: str) -> dict:
    import ast

    raiz = Path(caminho)
    funs = cls = docf = docc = tot_linhas = 0
    n_modulos = 0
    for p in sorted(raiz.rglob("*.py")):
        if any(part in {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"} for part in p.parts):
            continue
        n_modulos += 1
        try:
            texto = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tot_linhas += texto.count("\n") + 1
        try:
            tree = ast.parse(texto)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funs += 1
                if ast.get_docstring(node):
                    docf += 1
            elif isinstance(node, ast.ClassDef):
                cls += 1
                if ast.get_docstring(node):
                    docc += 1
    return {
        "modulos_python": n_modulos, "linhas": tot_linhas, "funcoes": funs, "classes": cls,
        "funcoes_com_docstring": docf, "classes_com_docstring": docc,
        "cobertura_docstring_pct": round(100 * docf / max(funs, 1), 1),
    }


def _arvore(caminho: str, maximo: int) -> str:
    raiz = Path(caminho)
    ignorar = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next"}
    linhas: list[str] = []
    cont = 0

    def walk(p: Path, prof: int) -> None:
        nonlocal cont
        try:
            filhos = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except OSError:
            return
        for child in filhos:
            if cont >= maximo:
                return
            if child.name in ignorar or child.name.startswith("."):
                continue
            linhas.append("  " * prof + (child.name + "/" if child.is_dir() else child.name))
            cont += 1
            if child.is_dir():
                walk(child, prof + 1)

    walk(raiz, 0)
    return "\n".join(linhas[:maximo]) or "(vazio)"


def chamar(nome: str, args: dict) -> dict:
    try:
        if nome == "pp_buscar_web":
            from . import pesquisa
            fontes = pesquisa.busca_web(args.get("query", ""), limite=int(args.get("limite", 6)))
            return _ok(json.dumps(fontes, ensure_ascii=False, indent=1) or "nenhum resultado")
        if nome == "pp_ler_pagina":
            from . import pesquisa
            return _ok(pesquisa.ler_pagina(args["url"])[:12000])
        if nome == "pp_arxiv":
            from . import pesquisa
            return _ok(json.dumps(pesquisa.buscar_arxiv(args.get("query", ""), limite=int(args.get("limite", 5))),
                                  ensure_ascii=False, indent=1))
        if nome == "pp_eval_python":
            codigo = args["code"]
            timeout = int(args.get("timeout_s", 60))
            prefixo = "import matplotlib; matplotlib.use('Agg')\n"
            with tempfile.TemporaryDirectory(prefix="pp-eval-") as tmp:
                env = dict(os.environ)
                env["MPLBACKEND"] = "Agg"
                proc = subprocess.run([sys.executable, "-c", prefixo + codigo], cwd=tmp, env=env,
                                      capture_output=True, text=True, timeout=timeout)
            saida = (proc.stdout or "")
            if proc.stderr.strip():
                saida += "\n[stderr]\n" + proc.stderr
            return _ok(saida[:8000] or "(sem saída)")
        if nome == "pp_stats":
            return _ok(_stats(args))
        if nome == "pp_ast_python":
            return _ok(json.dumps(_ast(args.get("caminho", ".")), ensure_ascii=False, indent=1))
        if nome == "pp_arvore":
            return _ok(_arvore(args.get("caminho", "."), int(args.get("maximo", 200))))
        if nome == "pp_dependencias":
            from . import analysis
            raiz = Path(args.get("caminho", ".")).resolve()
            m: dict[str, list[str]] = {}
            for nomef in ("pyproject.toml", "package.json", "go.mod", "Cargo.toml", "requirements.txt"):
                if (raiz / nomef).exists():
                    m[nomef] = analysis._deps_manifesto(nomef, (raiz / nomef).read_text(errors="replace")[:20000])
            return _ok(json.dumps(m, ensure_ascii=False, indent=1) or "nenhum manifesto encontrado")
        if nome == "pp_docx":
            from .exporter import docx as _docx
            md = args["markdown"]
            out = args.get("saida") or str(Path(md).with_suffix(".docx"))
            _docx.gerar_docx(Path(md), Path(out), titulo=args.get("titulo"), autor=args.get("autor", "Papo Pepper"))
            return _ok(f"gerado: {out}")
        if nome == "pp_pdf":
            from .exporter import pdf as _pdf
            md = args["markdown"]
            out = args.get("saida") or str(Path(md).with_suffix(".pdf"))
            engine = _pdf.gerar_pdf(Path(md), Path(out), titulo=args.get("titulo"), autor=args.get("autor", "Papo Pepper"))
            return _ok(f"gerado: {out} (engine: {engine})")
        return _erro(f"ferramenta desconhecida: {nome}")
    except KeyError as e:
        return _erro(f"argumento ausente: {e}")
    except subprocess.TimeoutExpired:
        return _erro("tempo esgotado (timeout_s)")
    except Exception as e:  # noqa: BLE001
        return _erro(f"{e.__class__.__name__}: {e}")


def principal() -> None:
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            msg = json.loads(linha)
        except json.JSONDecodeError:
            continue
        metodo = msg.get("method")
        mid = msg.get("id")
        resultado: dict | None = None
        erro: dict | None = None
        if metodo == "initialize":
            params = msg.get("params") or {}
            resultado = {
                "protocolVersion": params.get("protocolVersion") or "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "papo-pepper", "version": __version__},
            }
        elif metodo == "ping":
            resultado = {}
        elif metodo == "tools/list":
            resultado = {"tools": FERRAMENTAS}
        elif metodo == "tools/call":
            params = msg.get("params") or {}
            resultado = chamar(params.get("name", ""), params.get("arguments") or {})
        elif (metodo or "").startswith("notifications/"):
            continue
        elif mid is None:
            continue
        else:
            erro = {"code": -32601, "message": f"método não suportado: {metodo}"}
        saida: dict = {"jsonrpc": "2.0", "id": mid}
        if erro is not None:
            saida["error"] = erro
        else:
            saida["result"] = resultado
        sys.stdout.write(json.dumps(saida, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    principal()
