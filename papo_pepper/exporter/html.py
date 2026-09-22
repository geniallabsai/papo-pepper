"""Gera HTML standalone (CSS embutido) a partir do markdown do paper."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from html import escape as _esc

_ESTILO_CSS = Path(__file__).parent / "styles.css"


def gerar_html(markdown_texto: str, *, titulo: str, autor: str = "", data: str = "", base_dir: Path | None = None) -> str:
    css = _ESTILO_CSS.read_text(encoding="utf-8")
    corpo = _md_para_html(markdown_texto)
    corpo = _injetar_ids(corpo)
    toc = _toc_de(corpo)
    data = data or date.today().isoformat()
    meta_linha = f"{_esc(autor)} &nbsp;·&nbsp; {_esc(data)}" if autor else _esc(data)
    capa = (
        "<header class=\"capa\">"
        f"<h1 class=\"titulo\">{_esc(titulo)}</h1>"
        "<div class=\"linha\"></div>"
        f"<p class=\"meta\">{meta_linha}</p>"
        "<p class=\"assinatura\">Produzido pela equipe multi-agente <strong>Papo Pepper</strong></p>"
        "</header><hr class=\"quebra-caixa\">"
    )
    sumario = f"<nav class=\"sumario\"><h2>Sumário</h2>{toc}</nav>" if toc else ""
    return (
        "<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{_esc(titulo)}</title><style>{css}</style></head>"
        f"<body>{capa}{sumario}<main>{corpo}</main>"
        f"<footer class=\"rodape\">Papo Pepper · {date.today().isoformat()} · pipeline multi-agente de 12 papéis</footer></body></html>"
    )


def _md_para_html(texto: str) -> str:
    try:
        import markdown as _md
        return _md.markdown(texto, extensions=["extra", "tables", "fenced_code", "sane_lists"])
    except ImportError:
        return _mini_md(texto)


def _slug(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[^\w\sÀ-ÿ\-]", "", t, flags=re.U).strip().lower()
    return re.sub(r"\s+", "-", t)[:60] or "secao"


def _injetar_ids(corpo: str) -> str:
    vistos: dict[str, int] = {}

    def sub(m: re.Match) -> str:
        lvl, attrs, inner = m.group(1), m.group(2) or "", m.group(3)
        if " id=" in attrs:
            return m.group(0)
        s = _slug(inner)
        n = vistos.get(s, 0)
        vistos[s] = n + 1
        ident = s if n == 0 else f"{s}-{n}"
        return f"<h{lvl}{attrs} id=\"{ident}\">{inner}</h{lvl}>"

    return re.sub(r"<h([1-3])([^>]*)>(.*?)</h\1>", sub, corpo, flags=re.S)


def _toc_de(corpo: str) -> str:
    itens = re.findall(r"<h([1-3])[^>]*id=\"([^\"]+)\"[^>]*>(.*?)</h\1>", corpo, flags=re.S)
    if not itens:
        return ""
    linhas = ["<ol class=\"lista-toc\">"]
    for nivel, ident, rotulo in itens:
        rotulo = re.sub(r"<[^>]+>", "", rotulo).strip()
        linhas.append(f"<li class=\"nivel-{nivel}\"><a href=\"#{ident}\">{_esc(rotulo)}</a></li>")
    linhas.append("</ol>")
    return "".join(linhas)


# ------------------------------------------------------------------ fallback sem lib markdown
def _inline(t: str) -> str:
    t = re.sub(r"`([^`]+)`", lambda m: f"<code>{_esc(m.group(1))}</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"<img src=\"\2\" alt=\"\1\">", t)
    t = re.sub(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)", r'<a href="\"\2\">\"\1\"</a>'.replace('"', '"'), t)
    return t


def _mini_md(texto: str) -> str:
    saida: list[str] = []
    modo_lista = None  # 'ul' | 'ol' | None
    tabela: list[str] = []

    def fecha_tabela():
        nonlocal tabela
        if not tabela:
            return
        linhas_t = [l for l in tabela if not re.match(r"^\|?\s*:?-+:?\|", l)]
        if linhas_t:
            celulas = [[c.strip() for c in l.strip().strip("|").split("|")] for l in linhas_t]
            saida.append("<table>")
            for i, linha_c in enumerate(celulas):
                tag = "th" if i == 0 else "td"
                while len(linha_c) < max(len(x) for x in celulas):
                    linha_c.append("")
                saida.append("<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in linha_c) + "</tr>")
            saida.append("</table>")
        tabela = []

    i = 0
    linhas = texto.splitlines()
    in_fence = False
    fence_buf: list[str] = []
    paragrafo: list[str] = []

    def fecha_paragrafo():
        nonlocal paragrafo
        if paragrafo:
            saida.append("<p>" + _inline(_esc_html_novo(" ".join(paragrafo))) + "</p>")
            paragrafo = []

    def fecha_lista():
        nonlocal modo_lista
        if modo_lista:
            saida.append(f"</{modo_lista}>")
            modo_lista = None

    def _esc_html_novo(s):
        # paragrafo já escapado? não — escapa aqui, mas _inline já gera tags... simplificação:
        return s

    for linha in linhas:
        if linha.strip().startswith("```"):
            if in_fence:
                saida.append("<pre><code>" + _esc("\n".join(fence_buf)) + "</code></pre>")
                fence_buf = []
                in_fence = False
            else:
                fecha_paragrafo(); fecha_lista(); fecha_tabela()
                in_fence = True
            continue
        if in_fence:
            fence_buf.append(linha)
            continue
        if linha.lstrip().startswith("|"):
            fecha_paragrafo(); fecha_lista()
            tabela.append(linha)
            continue
        else:
            fecha_tabela()
        hm = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if hm:
            fecha_paragrafo(); fecha_lista()
            n = min(len(hm.group(1)), 4)
            saida.append(f"<h{n}>{_inline(_esc(hm.group(2).strip()))}</h{n}>")
            continue
        if re.match(r"^\s*([-*+])\s+", linha):
            marca = re.match(r"^\s*([-*+])", linha).group(1)
            conteudo = re.sub(r"^\s*[-*+]\s+", "", linha)
            if modo_lista != "ul":
                fecha_paragrafo(); fecha_lista()
                saida.append("<ul>")
                modo_lista = "ul"
            saida.append(f"<li>{_inline(_esc(conteudo))}</li>")
            continue
        mn = re.match(r"^\s*(\d+)[.)]\s+", linha)
        if mn:
            conteudo = re.sub(r"^\s*\d+[.)]\s+", "", linha)
            if modo_lista != "ol":
                fecha_paragrafo(); fecha_lista()
                saida.append("<ol>")
                modo_lista = "ol"
            saida.append(f"<li>{_inline(_esc(conteudo))}</li>")
            continue
        if linha.lstrip().startswith(">"):
            fecha_paragrafo(); fecha_lista()
            saida.append(f"<blockquote>{_inline(_esc(re.sub(r'^\\s*>\\s?', '', linha)))}</blockquote>")
            continue
        if linha.strip() in ("---", "***", "___"):
            fecha_paragrafo(); fecha_lista()
            saida.append("<hr>")
            continue
        if not linha.strip():
            fecha_paragrafo(); fecha_lista()
            continue
        paragrafo.append(linha.strip())
    if in_fence and fence_buf:
        saida.append("<pre><code>" + _esc("\n".join(fence_buf)) + "</code></pre>")
    fecha_paragrafo(); fecha_lista(); fecha_tabela()
    return "\n".join(saida)
