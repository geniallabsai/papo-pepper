"""Pesquisa profunda sem dependências pesadas: DuckDuckGo (HTML), arXiv (API Atom),
Semantic Scholar (opcional, S2_API_KEY). Melhor esforço — falhas de rede viram avisos.
"""
from __future__ import annotations

import html as html_mod
import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, unquote, urlparse

import httpx

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0 PapoPepper/0.1"


def busca_web(consulta: str, limite: int = 8, idioma: str = "br-pt") -> list[dict]:
    r = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": consulta, "kl": idioma},
        headers={"User-Agent": UA}, timeout=25, follow_redirects=True,
    )
    r.raise_for_status()
    pagina = r.text
    links = re.findall(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', pagina, re.S
    )
    trechos = [_limpar(t) for t in re.findall(
        r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|div)>', pagina, re.S
    )]
    out: list[dict] = []
    for i, (href, titulo) in enumerate(links[:limite]):
        url = _decodificar(href)
        if not url.startswith("http"):
            continue
        out.append({
            "origem": "web", "titulo": _limpar(titulo), "url": url,
            "trecho": trechos[i] if i < len(trechos) else "",
        })
    return out


def _decodificar(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    qs = parse_qs(urlparse(href).query)
    if "uddg" in qs:
        return unquote(qs["uddg"][0])
    return href


def _limpar(txt: str) -> str:
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html_mod.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


def ler_pagina(url: str, timeout: float = 25.0, max_chars: int = 24000) -> str:
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    return html_para_texto(r.text)[:max_chars]


def html_para_texto(html: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|section|article)>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html_mod.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    return t.strip()


def buscar_arxiv(consulta: str, limite: int = 5) -> list[dict]:
    r = httpx.get(
        "http://export.arxiv.org/api/query",
        params={"search_query": f"all:'{consulta}'", "start": 0, "max_results": limite},
        headers={"User-Agent": UA}, timeout=30,
    )
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    raiz = ET.fromstring(r.text)
    out: list[dict] = []
    for e in raiz.findall("a:entry", ns):
        out.append({
            "origem": "arxiv",
            "titulo": re.sub(r"\s+", " ", e.findtext("a:title", "", ns)).strip(),
            "url": (e.findtext("a:id", "", ns) or "").strip(),
            "autores": [x.findtext("a:name", "", ns) for x in e.findall("a:author", ns)],
            "trecho": re.sub(r"\s+", " ", e.findtext("a:summary", "", ns)).strip()[:400],
            "data": (e.findtext("a:published", "", ns) or "")[:10],
        })
    return out


def scholar(consulta: str, limite: int = 5) -> list[dict]:
    chave = os.getenv("S2_API_KEY")
    if not chave:
        return []
    r = httpx.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": consulta, "limit": limite},
        headers={"X-API-KEY": chave, "User-Agent": UA}, timeout=30,
    )
    r.raise_for_status()
    out: list[dict] = []
    for p in r.json().get("data", []):
        doi = (p.get("externalIds") or {}).get("DOI")
        url = f"https://doi.org/{doi}" if doi else f"https://www.semanticscholar.org/paper/{p.get('paperId')}"
        out.append({
            "origem": "scholar", "titulo": p.get("title", ""), "url": url,
            "trecho": (p.get("abstract") or "")[:300], "data": str(p.get("year") or ""),
        })
    return out


def pesquisar_profundo(consultas: list[str], limite: int = 8) -> tuple[list[dict], list[str]]:
    """Rodas web + arxiv + scholar sobre as consultas; retorna (fontes dedupeadas, avisos)."""
    fontes: list[dict] = []
    avisos: list[str] = []
    for q in consultas:
        for funcao, origem in ((busca_web, "web"), (buscar_arxiv, "arxiv"), (scholar, "scholar")):
            try:
                limite_q = limite if origem == "web" else max(3, limite // 2)
                fontes.extend(funcao(q, limite=limite_q))
            except Exception as e:  # noqa: BLE001 — rede é melhor esforço
                avisos.append(f"{origin}/{q[:40]}: {e.__class__.__name__}")
    return _dedup(fontes), avisos


def _dedup(fontes: list[dict]) -> list[dict]:
    vistos: set[str] = set()
    out: list[dict] = []
    for f in fontes:
        chave = (f.get("url") or f.get("titulo") or "").lower().strip()
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        f.setdefault("id", len(out) + 1)
        out.append(f)
    return out


def consultas_padrao(assunto: str, perguntas: list[str] | None = None) -> list[str]:
    consultas = [
        f"{assunto} state of the art",
        f"{assunto} review evidence",
    ]
    for p in (perguntas or [])[:3]:
        consultas.append(str(p)[:160])
    consultas.append(assunto)
    return consultas[:5]
