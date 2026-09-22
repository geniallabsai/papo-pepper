import json
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_pipeline_offline_gera_esqueletos_e_paper_final():
    from papo_pepper import intake as intake_mod
    from papo_pepper import orchestrator

    cfg = {"provider": "off", "autor": "QA Papo Pepper", "idioma": "pt-BR",
           "estilo_citacao": "apa", "formato_preferido": "pdf",
           "profundidade": "padrao", "diretorio_papers": "/tmp",
           "temperatura": 0.4, "max_tokens": 8192}
    with tempfile.TemporaryDirectory() as tmp:
        papel_dir = orchestrator.criar_papel(tmp, "Redes neurais para dobragem de proteínas", cfg)
        intake_mod.stub_intake(papel_dir, "Redes neurais para dobragem de proteínas",
                               tipo="cientifico", cfg=cfg)
        resumo = orchestrator.rodar(papel_dir, cfg, sem_internet=True)
        assert resumo.get("ok") is True

        esperados = ["00_intake.md", "01_plano.md", "02_notas_pesquisa.md",
                     "03_mapa_informacional.md", "05_relatorio_cetico.md",
                     "06_desafios.md", "07_validacao.md", "08_veredito.md",
                     "09_figuras.md", "10_manuscrito_final.md", "11_revisao.md",
                     "12_paper.md", "meta.json"]
        for nome in esperados:
            assert (papel_dir / nome).exists(), f"faltando artefato: {nome}"

        secoes = list((papel_dir / "04_secoes").glob("*.md"))
        assert len(secoes) >= 3, "especialista nao produziu secoes"

        final = (papel_dir / "12_paper.md").read_text(encoding="utf-8")
        corpo = "\n".join(l for l in final.splitlines() if not l.lstrip().startswith("<!--"))
        assert corpo.lstrip().startswith("#"), "paper final sem titulo (apos o marker de esqueleto)"
        assert "## Referências" in final, "referencias nao foram anexadas"

        meta = json.loads((papel_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta.get("titulo")
        assert meta.get("versao")

        linhas = (papel_dir / "log" / "pipeline.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(linhas) >= 11, "log da pipeline incompleto"
