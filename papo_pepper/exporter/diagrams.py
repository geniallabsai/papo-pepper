"""Figuras Mermaid: extração do manuscrito + renderização (mmdc → matplotlib → .mmd puro)."""
from __future__ import annotations

import re
import shutil
import subprocess
from collections import defaultdict, deque
from pathlib import Path


def extrair_mermaids(texto: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"```mermaid\s*\n(.*?)```", texto, re.S)]


def renderizar_mermaid(txt: str, saida: Path) -> Path:
    """Renderiza para PNG se houver mmdc ou matplotlib; senão preserva o .mmd."""
    saida_png = Path(str(saida)).with_suffix(".png")
    tmp = Path(str(saida) + ".src.mmd")
    tmp.write_text(txt, encoding="utf-8")

    mmdc = shutil.which("mmdc")
    if mmdc:
        r = subprocess.run([mmdc, "-i", str(tmp), "-o", str(saida_png), "-b", "white"],
                           capture_output=True, timeout=60)
        if r.returncode == 0 and saida_png.exists():
            return saida_png

    noes, arestas, rotulos = _parse(txt)
    if noes:
        try:
            _desenhar_matplotlib(noes, arestas, rotulos, saida_png)
            return saida_png
        except Exception:  # noqa: BLE001 — matplotlib ausente falha sem drama
            pass

    alvo = Path(str(saida) + ".mmd")
    alvo.write_text(txt, encoding="utf-8")
    return alvo


_NOE_ROTULO = re.compile(r'([A-Za-z_]\w*)\s*(?:\["?([^"\]]*)"?\]|\{"?([^"}{}]*)"?\}|\(\("?([^"(){}]*)"?\)\))')
_ARESTA = re.compile(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\]|\{[^}]*\}|\(\([^)]*\)\))?\s*(-{2,}>|-\.->|=->)\s*(?:\|([^|]*)\|)?\s*([A-Za-z_]\w*)")


def _parse(txt: str) -> tuple[set[str], list[tuple[str, str, str]], dict[str, str]]:
    noes: set[str] = set()
    rotulos: dict[str, str] = {}
    arestas: list[tuple[str, str, str]] = []
    for linha in txt.splitlines():
        l = linha.strip()
        if not l or l.startswith(("graph", "flowchart", "---", "%%", "subgraph", "end", "classDef", "linkStyle")):
            continue
        for m in _NOE_ROTULO.finditer(l):
            noes.add(m.group(1))
            rot = m.group(2) or m.group(3) or m.group(4) or ""
            if rot.strip() and m.group(1) not in rotulos:
                rotulos[m.group(1)] = rot.strip()
        ma = _ARESTA.match(l)
        if ma:
            a, rot, b = ma.group(1), (ma.group(3) or "").strip(), ma.group(4)
            noes.update((a, b))
            arestas.append((a, rot, b))
    for n in noes:
        rotulos.setdefault(n, n)
    return noes, arestas, rotulos


def _layout(noes: set[str], arestas: list[tuple[str, str, str]]) -> dict[str, tuple[int, float]]:
    adj: dict[str, list[str]] = defaultdict(list)
    indeg = {n: 0 for n in noes}
    for a, _, b in arestas:
        adj[a].append(b)
        indeg[b] = indeg.get(b, 0) + 1
    nivel: dict[str, int] = {}
    fila = deque(n for n in noes if indeg[n] == 0)
    if not fila and noes:
        fila.append(next(iter(noes)))
    for n in fila:
        nivel[n] = 0
    while fila:
        n = fila.popleft()
        for m in adj[n]:
            nivel[m] = max(nivel.get(m, -1), nivel.get(n, 0) + 1)
            indeg[m] -= 1
            if indeg[m] == 0:
                fila.append(m)
    resto = max(nivel.values(), default=0) + 1
    for n in noes:
        nivel.setdefault(n, resto)
    por_nivel: dict[int, list[str]] = defaultdict(list)
    for n in sorted(noes):
        por_nivel[nivel[n]].append(n)
    pos: dict[str, tuple[int, float]] = {}
    for nv, ns in por_nivel.items():
        for i, n in enumerate(ns):
            pos[n] = (nv, float(i - (len(ns) - 1) / 2))
    return pos


def _desenhar_matplotlib(noes, arestas, rotulos, saida: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    pos = _layout(noes, arestas)
    max_nivel = max(p[0] for p in pos.values()) if pos else 0
    mais_largo = max((len(r) for r in rotulos.values()), default=8)
    fig_w = (max_nivel + 1) * 3.9 + 2
    fig_h = max(3.2, max(len(v) for v in defaultdict(list, {}).values()) if False else 0)
    por_n: dict[int, int] = defaultdict(int)
    for x, y in pos.values():
        por_n[x] += 1
    fig_h = max(3.4, (max(por_n.values(), default=1)) * 2.1 + 1.2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    ax.axis("off")

    for n in sorted(pos):
        x, y = pos[n]
        cx, cy = x * 3.7, -y * 2.0
        larg = min(3.2, max(1.6, len(rotulos[n]) * 0.16 + 0.5))
        caixa = FancyBboxPatch((cx - larg / 2, cy - 0.62), larg, 1.24,
                               boxstyle="round,pad=0.06", linewidth=1.3,
                               edgecolor="#20242B", facecolor="#FFF7F0")
        ax.add_patch(caixa)
        ax.text(cx, cy, rotulos[n], ha="center", va="center", fontsize=8.8, color="#20242B")

    for a, rot, b in arestas:
        if a not in pos or b not in pos:
            continue
        xa, ya = pos[a][0] * 3.7, -pos[a][1] * 2.0
        xb, yb = pos[b][0] * 3.7, -pos[b][1] * 2.0
        seta = FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>", mutation_scale=13,
                               lw=1.3, color="#5A6472", connectionstyle="arc3,rad=0.08")
        ax.add_patch(seta)
        if rot:
            ax.text((xa + xb) / 2 + 0.15, (ya + yb) / 2 + 0.15, rot, fontsize=7.2, color="#8A4B3D")

    ax.set_xlim(-1.6, (max_nivel + 1) * 3.7 + 0.8)
    ys = [-p[1] * 2.0 for p in pos.values()]
    ax.set_ylim(min(ys) - 1.4, max(ys) + 1.4)
    fig.tight_layout()
    fig.savefig(saida, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def gerar_figuras(paper_dir: Path, caminho_paper: Path | None = None) -> list[dict]:
    """Extrai blocos mermaid do paper/seções, renderiza em figuras/ e devolve o índice."""
    paper_dir = Path(paper_dir)
    pastas_fig = paper_dir / "figuras"
    pastas_fig.mkdir(exist_ok=True)
    textos: list[str] = []
    if caminho_paper and caminho_paper.exists():
        textos.append(caminho_paper.read_text(encoding="utf-8"))
    for arq in sorted((paper_dir / "04_secoes").glob("*.md")):
        textos.append(arq.read_text(encoding="utf-8"))
    blocos = []
    for t in textos:
        blocos.extend(extrair_mermaids(t))
    indice: list[dict] = []
    vistos: set[str] = set()
    for i, bloco in enumerate(blocos, 1):
        if bloco in vistos:
            continue
        vistos.add(bloco)
        slug = re.sub(r"[^\w-]+", "-", (bloco.splitlines()[0][:30] or f"fig")).strip("-")
        mmd = pastas_fig / f"fig_{i:02d}_{slug}.mmd"
        mmd.write_text(bloco, encoding="utf-8")
        rota = renderizar_mermaid(bloco, pastas_fig / f"fig_{i:02d}_{slug}")
        indice.append({"numero": i, "fonte": str(mmd.name), "render": str(rota.name)})
    return indice
