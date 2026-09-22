"""Fontes (02_fontes.json) → BibTeX (referencias.bib)."""
from __future__ import annotations

import json
import re
from pathlib import Path


def _chave(autor: str, ano: str, titulo: str, n: int) -> str:
    base = re.sub(r"[^a-z]", "", autor.lower())[:12] or "fonte"
    ano = re.sub(r"[^0-9]", "", ano)[:4] or str(n)
    palavra = re.sub(r"[^a-z]", "", titulo.lower())[:8] or "papel"
    return f"{base}{ano}{palavra}"


def _esc(v: str) -> str:
    return v.replace("\\", r"\\\\").replace("{", r"\{").replace("}", r"\}").replace("&", r"\&").replace("%", r"\%")


def gerar_bibtex(fontes: list[dict], out: Path | str) -> Path:
    out = Path(out)
    linhas = ["% Gerado por Papo Pepper (exporter/bib.py)", "% Nível de citação conforme o mapa informacional do paper.", ""]
    chaves_usadas: set[str] = set()
    for i, f in enumerate(fontes, 1):
        auto = f.get("autores") or []
        autor_txt = " and ".join(auto[:6]) if isinstance(auto, list) else str(auto or "Anônimo")
        data = str(f.get("data") or "")
        ano = re.sub(r"\D", "", data)[:4]
        if not ano:
            ano = str(i)
        chave = _chave(autor_txt.split()[0] if autor_txt else "fonte", ano, str(f.get("titulo", "")), i)
        sufixo = 2
        while chave in chaves_usadas:
            chave += str(sufixo)
            sufixo += 1
        chaves_usadas.add(chave)
        url = str(f.get("url", ""))
        extra = ""
        if "arxiv.org" in url:
            m = re.search(r"abs/(\d{4}\.\d+)", url)
            if m:
                extra = ",\n  eprint         = {" + m.group(1) + "},\n  archivePrefix  = {arXiv}"
        entradas = [
            "  title          = {" + _esc(str(f.get("titulo", ""))) + "}",
            "  author         = {" + _esc(autor_txt) + "}",
            "  year           = {" + ano + "}",
            r"  howpublished   = {\url{" + _esc(url) + "}}",
        ]
        linhas.append("@misc{" + chave + ",\n" + ",\n".join(entradas) + extra + "\n}\n")
    out.write_text("\n".join(linhas), encoding="utf-8")
    return out
