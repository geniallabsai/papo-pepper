"""PDF do paper — cadeia de engines: weasyprint (HTML+CSS) → reportlab → fpdf2.

Cada engine degrada graciosamente; o fallback final (fpdf2) é puro Python e sempre funciona.
"""
from __future__ import annotations

import re
from pathlib import Path

from .html import gerar_html as _gerar_html


def gerar_pdf(md_caminho: str | Path, out: str | Path, *, titulo: str | None = None,
              autor: str = "", data: str = "", resumo: str = "") -> str:
    """Retorna o nome da engine que produziu o PDF."""
    md_caminho = Path(md_caminho)
    out = Path(out)
    md = md_caminho.read_text(encoding="utf-8")
    if not titulo:
        m = re.search(r"^#\s+(.+)$", md, flags=re.M)
        titulo = m.group(1).strip() if m else md_caminho.stem
    erros: list[str] = []

    html_doc = _gerar_html(md, titulo=titulo, autor=autor, data=data, base_dir=md_caminho.parent)
    try:
        from weasyprint import HTML
        HTML(string=html_doc, base_url=str(md_caminho.parent)).write_pdf(str(out))
        return "weasyprint"
    except ImportError:
        erros.append("weasyprint: não instalado (pip install weasyprint)")
    except Exception as e:  # noqa: BLE001 — libs de sistema ausentes são comuns
        erros.append(f"weasyprint: {e.__class__.__name__}")

    try:
        _pdf_reportlab(md, out, titulo, autor, data, resumo)
        return "reportlab"
    except ImportError:
        erros.append("reportlab: não instalado (pip install reportlab)")
    except Exception as e:  # noqa: BLE001
        erros.append(f"reportlab: {e.__class__.__name__}")

    _pdf_fpdf(md, out, titulo, autor, data)
    if erros:
        print(f"[papo-pepper] pdf via fpdf2 — engines anteriores indisponíveis: {'; '.join(erros)}")
    return "fpdf2"


# ---------------------------------------------------------------- reportlab
def _rl_inline(t: str) -> str:
    """Markdown inline -> tags reportlab (sentinelas para não disputar com o escape)."""
    t = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", r"[figura: \1]", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    t = re.sub(r"`([^`]+)`", "\x00C\x00" + r"\1" + "\x00c\x00", t)
    t = re.sub(r"\*\*([^*]+)\*\*", "\x00b\x00" + r"\1" + "\x00B\x00", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", "\x00i\x00" + r"\1" + "\x00I\x00", t)
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = t.replace("\x00C\x00", "<font face=\"Courier\" size=\"8.5\">")
    t = t.replace("\x00c\x00", "</font>")
    t = t.replace("\x00b\x00", "<b>").replace("\x00B\x00", "</b>")
    t = t.replace("\x00i\x00", "<i>").replace("\x00I\x00", "</i>")
    return t
def _pdf_reportlab(md: str, out: Path, titulo: str, autor: str, data: str, resumo: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (HRFlowable, PageBreak, Paragraph, Preformatted,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)

    est = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=est["Heading1"], fontSize=19, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#C8442C"))
    h2 = ParagraphStyle("H2", parent=est["Heading2"], fontSize=14.5, spaceBefore=12, spaceAfter=5, textColor=colors.HexColor("#20242B"))
    h3 = ParagraphStyle("H3", parent=est["Heading3"], fontSize=12, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#20242B"))
    corpo = ParagraphStyle("Corpo", parent=est["BodyText"], fontSize=10.5, leading=15.5)
    mono = ParagraphStyle("Mono", parent=est["Code"], fontSize=8.5, leading=11.5, backColor=colors.HexColor("#F4F1EA"))
    small = ParagraphStyle("Small", parent=est["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#5A6472"))

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=titulo, author=autor)
    story = []
    story.append(Spacer(1, 5.5 * cm))
    story.append(Paragraph("P A P O &nbsp;&nbsp; P E P P E R", ParagraphStyle("brand", parent=est["Title"], fontSize=12, alignment=1, textColor=colors.HexColor("#C8442C"))))
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph(_rl_inline(titulo), ParagraphStyle("tt", parent=est["Title"], fontSize=24, leading=30, alignment=1)))
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="35%", thickness=2, color=colors.HexColor("#C8442C"), hAlign="CENTER"))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"{_rl_inline(autor)} &nbsp;·&nbsp; {data}", ParagraphStyle("meta", parent=small, alignment=1)))
    if resumo:
        story.append(Spacer(1, 1.4 * cm))
        story.append(Paragraph(_rl_inline(resumo[:700]), ParagraphStyle("res", parent=small, alignment=0)))
    story.append(PageBreak())

    linhas = md.splitlines()
    i, n = 0, len(linhas)
    while i < n:
        linha = linhas[i]
        if not linha.strip():
            i += 1
            continue
        if linha.strip().startswith("```"):
            i += 1
            buf = []
            while i < n and not linhas[i].strip().startswith("```"):
                buf.append(linhas[i])
                i += 1
            i += 1
            story.append(Preformatted("\n".join(buf), mono))
            story.append(Spacer(1, 4))
            continue
        if linha.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:\-|]+\|\s*$", linhas[i + 1]):
            celulas = []
            while i < n and linhas[i].lstrip().startswith("|"):
                celulas.append([c.strip() for c in linhas[i].strip().strip("|").split("|")])
                i += 1
            celulas = [c for j, c in enumerate(celulas) if j != 1]
            if celulas:
                larguras = max(len(c) for c in celulas)
                dados = []
                for r_i, c in enumerate(celulas):
                    while len(c) < larguras:
                        c.append("")
                    dados.append([Paragraph(_rl_inline(x), small if r_i else ParagraphStyle("th", parent=small, fontName="Helvetica-Bold", textColor=colors.white, backColor=colors.HexColor("#20242B"))) for x in c])
                t = Table(dados, colWidths=[16.5 / larguras * cm] * larguras)
                t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8D2C4")),
                                       ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#FAF8F3")])]))
                story.append(t)
                story.append(Spacer(1, 6))
            continue
        hm = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if hm:
            nivel = min(len(hm.group(1)), 3)
            texto = re.sub(r"<[^>]+>", "", hm.group(2)).strip()
            story.append(Paragraph(_rl_inline(texto), (h1, h2, h3)[nivel - 1]))
            i += 1
            continue
        if linha.strip() in ("---", "***", "___"):
            story.append(Spacer(1, 6))
            i += 1
            continue
        if re.match(r"^\s*[-*+]\s+", linha):
            conteudo = re.sub(r"^\s*[-*+]\s+", "", linha)
            story.append(Paragraph("•&nbsp;&nbsp;" + _rl_inline(conteudo), ParagraphStyle("bl", parent=corpo, leftIndent=14)))
            i += 1
            continue
        mn = re.match(r"^\s*(\d+)[.)]\s+", linha)
        if mn:
            conteudo = re.sub(r"^\s*\d+[.)]\s+", "", linha)
            story.append(Paragraph(f"{mn.group(1)}.&nbsp;&nbsp;" + _rl_inline(conteudo), ParagraphStyle("nl", parent=corpo, leftIndent=14)))
            i += 1
            continue
        if linha.lstrip().startswith(">"):
            conteudo = re.sub(r"^\s*>\s?", "", linha)
            story.append(Paragraph(_rl_inline(conteudo), ParagraphStyle("q", parent=corpo, leftIndent=12, textColor=colors.HexColor("#3A414C"), fontName="Helvetica-Oblique")))
            i += 1
            continue
        mimg = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", linha.strip())
        if mimg:
            caminho = (Path(mimg.group(2)))
            if not caminho.is_absolute():
                caminho = out.parent / mimg.group(2)
            if caminho.exists():
                try:
                    from PIL import Image
                    with Image.open(caminho) as im:
                        w, hgt = im.size
                    larg = 16 * cm
                    story.append(_centro_imagem(caminho, larg, hgt / w * larg))
                except Exception:  # noqa: BLE001
                    story.append(Paragraph(f"[figura: {mimg.group(1)}]", small))
            i += 1
            continue
        story.append(Paragraph(_rl_inline(linha.strip()), corpo))
        i += 1

    def _on_page(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#8A8377"))
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"Papo Pepper · página {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)


def _centro_imagem(caminho: Path, largura, altura):
    from reportlab.platypus import Image as RLImage, Table
    img = RLImage(str(caminho), width=largura, height=altura)
    t = Table([[img]], colWidths=[16 * __import__("reportlab.lib.units", fromlist=["cm"]).cm])
    t.setStyle(__import__("reportlab.platypus", fromlist=["TableStyle"]).TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    t.hAlign = "CENTER"
    return t


# ---------------------------------------------------------------- fpdf2 (fallback puro python)
_FP_SUBS = {"•": "-", "·": "-", "–": "-", "—": "-", "…": "...", "‘": "'", "’": "'",
            "“": '"', "”": '"', "✅": "[OK]", "❌": "[X]", "⚠": "(!)", "🌶": "", "️": ""}


def _latin1(t: str) -> str:
    for a, b in _FP_SUBS.items():
        t = t.replace(a, b)
    return "".join(ch for ch in t if ord(ch) < 256)


def _fp_esc(t: str) -> str:
    t = re.sub(r"!\[[^\]]*\]\(([^)]+)\)", r"[figura: \1]", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    t = t.replace("**", "").replace("*", "").replace("`", "")
    return _latin1(t)


def _pdf_fpdf(md: str, out: Path, titulo: str, autor: str, data: str) -> None:
    from fpdf import FPDF

    class Pape(FPDF):
        def header(self):
            if self.page_no() > 1:
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(150, 145, 135)
                self.cell(0, 8, _latin1((titulo or "Papo Pepper")[:80]), align="C")
                self.ln(5)
            else:
                self.ln(5)

        def footer(self):
            self.set_y(-14)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(120, 115, 105)
            self.cell(0, 10, f"Página {self.page_no()}/{self.alias_nb_pages()}", align="C")

    f = Pape(format="A4", unit="mm")
    f.set_margins(18, 16, 18)
    f.add_page()
    f.set_font("Helvetica", "B", 11)
    f.set_text_color(200, 68, 44)
    f.cell(0, 10, "P A P O   P E P P E R", align="C")
    f.ln(18)
    f.set_font("Helvetica", "B", 22)
    f.set_text_color(32, 36, 43)
    f.multi_cell(0, 11, titulo or "", align="C")
    y = f.get_y() + 3
    f.set_draw_color(200, 68, 44)
    f.line(72, y, 143, y)
    f.ln(8)
    f.set_font("Helvetica", "", 11)
    f.set_text_color(90, 100, 114)
    f.cell(0, 7, f"{autor or ''}  ·  {data or ''}", align="C")
    f.add_page()

    linhas = md.splitlines()
    i, n = 0, len(linhas)
    while i < n:
        linha = linhas[i]
        if not linha.strip():
            i += 1
            continue
        if linha.strip().startswith("```"):
            i += 1
            buf = []
            while i < n and not linhas[i].strip().startswith("```"):
                buf.append(linhas[i])
                i += 1
            i += 1
            f.set_font("Courier", "", 8.5)
            f.set_fill_color(244, 241, 234)
            for b in buf or [" "]:
                f.multi_cell(0, 4.6, _fp_esc(b)[:200], fill=True)
            f.ln(2)
            f.set_font("Helvetica", "", 10.5)
            continue
        if linha.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:\-|]+\|\s*$", linhas[i + 1]):
            celulas = []
            while i < n and linhas[i].lstrip().startswith("|"):
                celulas.append([c.strip() for c in linhas[i].strip().strip("|").split("|")])
                i += 1
            celulas = [c for j, c in enumerate(celulas) if j != 1]
            if celulas:
                nc = max(len(c) for c in celulas)
                lw = 174 / nc
                f.set_font("Helvetica", "B", 8.5)
                for c in celulas:
                    for k in range(nc):
                        txt = c[k] if k < len(c) else ""
                        f.cell(lw, 6.5, txt[: int(lw / 1.7)], border=1,
                               fill=(celulas.index(c) == 0))
                    f.ln()
                f.ln(2)
            f.set_font("Helvetica", "", 10.5)
            continue
        hm = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if hm:
            nv = len(hm.group(1))
            tam = {1: 17, 2: 14, 3: 12}.get(nv, 11)
            f.set_font("Helvetica", "B", tam)
            f.set_text_color(200, 68, 44 if nv == 1 else 32, 200, 68, 44 if nv == 1 else 43) if False else None
            if nv == 1:
                f.set_text_color(200, 68, 44)
            else:
                f.set_text_color(32, 36, 43)
            f.multi_cell(0, 8, _fp_esc(hm.group(2).strip()))
            f.ln(1.5)
            f.set_font("Helvetica", "", 10.5)
            f.set_text_color(32, 36, 43)
            i += 1
            continue
        if linha.strip() in ("---", "***", "___"):
            i += 1
            continue
        if re.match(r"^\s*[-*+]\s+", linha):
            conteudo = re.sub(r"^\s*[-*+]\s+", "", linha)
            f.multi_cell(0, 5.6, "-  " + _fp_esc(conteudo), new_x="LMARGIN", new_y="NEXT")
            i += 1
            continue
        mn = re.match(r"^\s*(\d+)[.)]\s+", linha)
        if mn:
            conteudo = re.sub(r"^\s*\d+[.)]\s+", "", linha)
            f.multi_cell(0, 5.6, f"{mn.group(1)}.  " + _fp_esc(conteudo), new_x="LMARGIN", new_y="NEXT")
            i += 1
            continue
        if linha.lstrip().startswith(">"):
            conteudo = re.sub(r"^\s*>\s?", "", linha)
            f.set_font("Helvetica", "I", 10)
            f.set_text_color(58, 65, 76)
            f.multi_cell(0, 5.4, _latin1("“" + _fp_esc(conteudo) + "”"), new_x="LMARGIN", new_y="NEXT")
            f.set_font("Helvetica", "", 10.5)
            f.set_text_color(32, 36, 43)
            i += 1
            continue
        mimg = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", linha.strip())
        if mimg:
            caminho = Path(mimg.group(2))
            if not caminho.is_absolute():
                caminho = out.parent / mimg.group(2)
            if caminho.exists():
                try:
                    from PIL import Image
                    with Image.open(caminho) as im:
                        w, hgt = im.size
                    larg = 160
                    f.image(str(caminho), w=larg)
                    f.ln(hgt / w * larg + 3)
                except Exception:  # noqa: BLE001
                    f.cell(0, 5, f"[figura: {mimg.group(1)}]")
                    f.ln(6)
            i += 1
            continue
        f.multi_cell(0, 5.6, _fp_esc(linha.strip()), align="J", new_x="LMARGIN", new_y="NEXT")
        i += 1
    f.output(str(out))
