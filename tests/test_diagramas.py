import tempfile
from pathlib import Path


def test_extrai_bloco_mermaid():
    from papo_pepper.exporter import diagrams
    md = "texto antes\n\n```mermaid\ngraph TD\n  A[Coletar] --> B[Processar]\n  B --> C[Decidir]\n```\n\ntexto depois"
    blocos = diagrams.extrair_mermaids(md)
    assert len(blocos) == 1
    assert "A[Coletar]" in blocos[0]


def test_renderiza_mermaid_em_png():
    from papo_pepper.exporter import diagrams
    txt = "graph TD\n  A[Coletar] --> B[Processar]\n  B --> C[Decidir]"
    with tempfile.TemporaryDirectory() as tmp:
        out = diagrams.renderizar_mermaid(txt, Path(tmp) / "fig.png")
        assert out is not None
        assert out.exists() and out.stat().st_size > 500
        if out.suffix == ".png":
            assert b"PNG" in out.read_bytes()[:8]
