"""Exportação do paper: HTML standalone, .docx profissional, PDF (3 engines) e BibTeX."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


def _primeiro_titulo(texto: str) -> str:
    m = re.search(r"^#\s+(.+)$", texto, flags=re.M)
    return m.group(1).strip() if m else ""


def exportar_paper(paper_dir: str | Path, formatos: list[str] | None = None) -> list[Path]:
    """Gera os artefatos finais em `paper_dir`. Retorna os caminhos gerados."""
    from . import bib, docx, html, pdf

    paper_dir = Path(paper_dir)
    formatos = [f.lower() for f in formatos] if formatos else ["html", "word", "pdf", "bib"]
    caminho_md: Path | None = None
    for nome in ("12_paper.md", "10_manuscrito_final.md"):
        if (paper_dir / nome).exists():
            caminho_md = paper_dir / nome
            break
    if caminho_md is None:
        raise FileNotFoundError(f"Não há manuscrito para exportar em {paper_dir} (procurei 12_paper.md e 10_manuscrito_final.md).")

    texto = caminho_md.read_text(encoding="utf-8")
    meta: dict = {}
    meta_path = paper_dir / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    titulo = meta.get("titulo") or _primeiro_titulo(texto) or paper_dir.name
    autor = meta.get("autor", "Equipe Papo Pepper")
    data = meta.get("data", date.today().isoformat())
    resumo = meta.get("resumo", "")
    palavras_chave = ", ".join(meta.get("palavras_chave", []))

    gerados: list[Path] = []
    if "html" in formatos:
        out = paper_dir / "paper.html"
        out.write_text(html.gerar_html(texto, titulo=titulo, autor=autor, data=data, base_dir=paper_dir), encoding="utf-8")
        gerados.append(out)
    if "word" in formatos:
        out = paper_dir / "paper.docx"
        docx.gerar_docx(caminho_md, out, titulo=titulo, autor=autor, data=data,
                        resumo=resumo, palavras_chave=palavras_chave)
        gerados.append(out)
    if "pdf" in formatos:
        out = paper_dir / "paper.pdf"
        pdf.gerar_pdf(caminho_md, out, titulo=titulo, autor=autor, data=data, resumo=resumo)
        gerados.append(out)
    if "bib" in formatos:
        fontes_arq = paper_dir / "02_fontes.json"
        fontes = []
        if fontes_arq.exists():
            try:
                fontes = json.loads(fontes_arq.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                fontes = []
        if fontes:
            gerados.append(bib.gerar_bibtex(fontes, paper_dir / "referencias.bib"))
    return gerados
