"""Orquestra a pipeline multi-agente sobre um diretório de paper."""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

from . import analysis, pesquisa
from .agents import base
from .console import consola
from .exporter import diagrams

MARCA_ESQUELETO = base.MARCA_ESQUELETO


def slugify(texto: str, maximo: int = 48) -> str:
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s-]", "", t, flags=re.U).strip().lower()
    return re.sub(r"[\s_-]+", "-", t)[:maximo].strip("-") or "paper"


def criar_papel(diretorio_raiz: str | Path, assunto: str, cfg: dict) -> Path:
    raiz = Path(diretorio_raiz or cfg.get("diretorio_papers", "papers")).expanduser()
    pasta = raiz / f"{date.today().strftime('%Y%m%d')}-{slugify(assunto)}"
    (pasta / base.SECOES_DIR).mkdir(parents=True, exist_ok=True)
    (pasta / "figuras").mkdir(exist_ok=True)
    (pasta / "log").mkdir(exist_ok=True)
    return pasta


def _ler_plano(paper_dir: Path) -> dict:
    plano_arq = paper_dir / base.PLANO
    if not plano_arq.exists():
        return {}
    from . import llm as _llm
    texto = plano_arq.read_text(encoding="utf-8")
    if _llm and isinstance(texto, str):
        m = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.S)
        if m:
            try:
                dado = json.loads(m.group(1))
                if isinstance(dado, dict):
                    return dado
            except json.JSONDecodeError:
                pass
    return {}


def _meta_intake(paper_dir: Path) -> dict:
    caminho = paper_dir / base.INTAKE
    if not caminho.exists():
        return {}
    m = re.search(r"```yaml\s*(.*?)```", caminho.read_text(encoding="utf-8"), re.S)
    if not m:
        return {}
    try:
        import yaml
        dados = yaml.safe_load(m.group(1))
        return dados if isinstance(dados, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _coletar_fontes(paper_dir: Path, ctx: dict, cfg: dict) -> tuple[list[dict], list[str]]:
    plano = _ler_plano(paper_dir)
    assunto = (ctx.get("assunto") or _meta_intake(paper_dir).get("assunto") or "tema do paper")
    consultas = pesquisa.consultas_padrao(str(assunto), plano.get("perguntas_pesquisa"))
    consola.print(f"    [dim]deep research: {len(consultas)} consultas (web + arXiv + scholar)…[/dim]")
    fontes, avisos = pesquisa.pesquisar_profundo(consultas, limite=8)
    existente = paper_dir / base.FONTES
    if existente.exists():
        try:
            velhas = json.loads(existente.read_text(encoding="utf-8"))
            vistas = {(f.get("url") or "").lower() for f in velhas}
            for f in fontes:
                if (f.get("url") or "").lower() not in vistas:
                    velhas.append(f)
            fontes = velhas
        except json.JSONDecodeError:
            pass
    for i, f in enumerate(fontes, 1):
        f.setdefault("id", i)
    (paper_dir / base.FONTES).write_text(json.dumps(fontes, ensure_ascii=False, indent=1), encoding="utf-8")
    return fontes, avisos


def _plano_eh_exemplo(plano: dict) -> bool:
    """True se o JSON veio do esqueleto do editor (placeholders), não de um plano real."""
    if not plano:
        return True
    texto = json.dumps(plano, ensure_ascii=False).lower()
    marcadores = ["sem clichê", "termo1", "pergunta 1", "testável", "o que esta seção entrega"]
    return sum(m in texto for m in marcadores) >= 2


def _secoes_do_plano(plano: dict) -> list[dict]:
    secoes = plano.get("secoes") or []
    keep = []
    for s in secoes:
        if isinstance(s, dict) and str(s.get("titulo", "")).lower() != "referências":
            keep.append(s)
    if not keep:
        keep = [{"titulo": "1. Introdução e problema", "foco": "planta o tema e a contribuição"},
                {"titulo": "2. Estado da arte", "foco": "o que já existe e onde está o buraco"},
                {"titulo": "3. Abordagem proposta", "foco": "método/arquitetura com detalhes executáveis"},
                {"titulo": "4. Evidência e resultados", "foco": "dados, benchmarks, cálculos verificados"},
                {"titulo": "5. Discussão crítica e limites", "foco": "o que aguenta ataque e o que não aguenta"},
                {"titulo": "6. Conclusão", "foco": "o que o leitor usa amanhã"}]
    return keep


def _executar(rolo, ctx, cfg, tem_llm) -> str:
    if tem_llm:
        return base.executar(rolo, ctx, cfg)
    return base.esqueleto(rolo, ctx)


def rodar(paper_dir: str | Path, cfg: dict, *, modo: str | None = None, desde: str | None = None,
          ate: str | None = None, forcar: bool = False, sem_internet: bool = False,
          extra_ctx: dict | None = None) -> dict:
    from . import llm

    paper_dir = Path(paper_dir)
    pipeline = base.PIPELINE_REPO if modo == "repo" else base.PIPELINE_PADRAO
    if desde:
        pipeline = pipeline[pipeline.index(desde):]
    if ate:
        pipeline = pipeline[: pipeline.index(ate) + 1]
    meta_intake = _meta_intake(paper_dir)
    cfg_visivel = {
        "assunto": meta_intake.get("assunto", ""),
        "publico": meta_intake.get("publico") or cfg.get("autor", ""),
        "tipo": meta_intake.get("tipo") or "tecnico",
        "idioma": cfg.get("idioma", "pt-BR"),
        "estilo_citacao": meta_intake.get("citacao") or cfg.get("estilo_citacao", "apa"),
        "profundidade": meta_intake.get("profundidade") or cfg.get("profundidade", "padrao"),
        "autor": cfg.get("autor", "Equipe Papo Pepper"),
        "data": date.today().isoformat(),
    }
    log_path = paper_dir / "log" / "pipeline.jsonl"
    resultados: list[dict] = []

    def log(linha: dict) -> None:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(linha, ensure_ascii=False) + "\n")

    tem_llm = llm.disponivel(cfg)
    if not tem_llm:
        consola.print("[yellow]Modo esqueleto ativo: cada etapa gera um CARTÃO DO AGENTE para completar "
                      "(por um LLM conectado ou por um agente como Claude Code/Codex/OpenClaw/Hermes).[/yellow]")

    for idx, rolo_id in enumerate(pipeline, 1):
        rolo = base.POR_ID[rolo_id]
        destino = paper_dir / rolo.artefato
        ja_feito = (destino.is_file() and not (MARCA_ESQUELETO in destino.read_text(encoding="utf-8")[:300]))
        if ja_feito and not forcar:
            consola.print(f"  [{idx:2d}/{len(pipeline)}] {rolo.emoji} {rolo.nome:24s} → [dim]mantido ({rolo.artefato})[/dim]")
            resultados.append({"rolo": rolo_id, "status": "mantido"})
            continue
        consola.print(f"  [{idx:2d}/{len(pipeline)}] {rolo.emoji} [bold]{rolo.nome}[/] → {rolo.artefato}")
        inicio = time.time()
        try:
            ctx = base.contextuar(paper_dir)
            ctx.update(cfg_visivel)
            ctx.update(extra_ctx or {})
            status = "ok"
            saida = ""
            if rolo_id == "pesquisador":
                fontes_coletadas, avisos = ([], ["modo offline/coleta desativada"])
                if not sem_internet:
                    try:
                        fontes_coletadas, avisos = _coletar_fontes(paper_dir, ctx, cfg)
                    except Exception as e:  # noqa: BLE001 — rede é melhor esforço
                        avisos = [f"falha de coleta: {e.__class__.__name__}: {e}"]
                ctx["fontes_coletadas"] = json.dumps(fontes_coletadas, ensure_ascii=False, indent=1)[:9000] or "(nenhuma fonte coletada automaticamente — use suas ferramentas de web/MCP)"
                ctx["avisos_coleta"] = "; ".join(avisos) or "ningum"
                saida = _executar(rolo, ctx, cfg, tem_llm)
                if tem_llm:
                    try:
                        lista = llm.extrair_json(saida)
                        if isinstance(lista, list) and lista and all(isinstance(x, dict) for x in lista):
                            (paper_dir / base.FONTES).write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")
                            status = "ok + fontes refinadas"
                    except Exception:  # noqa: BLE001
                        status = "ok (JSON de fontes não parseado)"
                destino.write_text(saida, encoding="utf-8")
            elif rolo_id == "especialista":
                plano = _ler_plano(paper_dir)
                if _plano_eh_exemplo(plano):
                    plano = {}
                profundidade = cfg_visivel["profundidade"]
                alvo = 1200 if profundidade == "maxima" else 700
                feitas: list[str] = []
                falhas: list[str] = []
                for n_sec, sec in enumerate(_secoes_do_plano(plano), 1):
                    titulo_sec = str(sec.get("titulo", f"{n_sec}. Seção"))
                    slug_sec = slugify(titulo_sec.replace(r"\d+\.\s*", "")) or f"secao-{n_sec}"
                    caminho_sec = paper_dir / base.SECOES_DIR / f"{n_sec:02d}_{slug_sec}.md"
                    if caminho_sec.exists() and not forcar and not (MARCA_ESQUELETO in caminho_sec.read_text(encoding="utf-8")[:300]):
                        feitas.append(titulo_sec)
                        continue
                    consola.print(f"       … seção: {titulo_sec}")
                    ctx_sec = dict(ctx)
                    ctx_sec["secao_titulo"] = titulo_sec
                    ctx_sec["secao_foco"] = str(sec.get("foco", ""))
                    ctx_sec["palavras_alvo"] = str(alvo)
                    ctx_sec["secoes_anteriores"] = "\n\n---\n\n".join(base._unir_secoes(paper_dir).split("---"))[-12000:]
                    try:
                        texto_sec = _executar(rolo, ctx_sec, cfg, tem_llm)
                        caminho_sec.write_text(texto_sec, encoding="utf-8")
                        feitas.append(titulo_sec)
                    except Exception as e:  # noqa: BLE001
                        caminho_sec.write_text(base.esqueleto(rolo, ctx_sec), encoding="utf-8")
                        falhas.append(f"{titulo_sec}: {e.__class__.__name__}")
                destino.mkdir(parents=True, exist_ok=True)
                saida = f"Seções escritas: {len(feitas)}. Falhas: {len(falhas)}"
                status = "ok" if not falhas else "ok com falhas → esqueleto nas falhas"
            elif rolo_id == "juiz":
                saida = _executar(rolo, ctx, cfg, tem_llm)
                destino.write_text(saida, encoding="utf-8")
                if tem_llm:
                    try:
                        (paper_dir / "log" / "veredito.json").write_text(
                            json.dumps(llm.extrair_json(saida), ensure_ascii=False, indent=1), encoding="utf-8")
                    except Exception:  # noqa: BLE001
                        pass
            elif rolo_id == "diagramador":
                saida = _executar(rolo, ctx, cfg, tem_llm)
                destino.write_text(saida, encoding="utf-8")
                indice = diagrams.gerar_figuras(paper_dir, destino)
                if indice:
                    destino.write_text(
                        saida + "\n\n## Arquivos gerados\n\n" +
                        "\n".join(f"- Figura {i['numero']}: `{i['render']}` (fonte: `{i['fonte']}`)" for i in indice) + "\n",
                        encoding="utf-8")
                status = "ok + figuras renderizadas" if indice else "ok"
            elif rolo_id == "revisor":
                saida = _executar(rolo, ctx, cfg, tem_llm)
                if tem_llm:
                    corpo, separador, changelog = saida.partition("## Changelog de revisão")
                    if separador:
                        (paper_dir / base.REVISAO).write_text("## Changelog de revisão\n" + changelog.lstrip("\n"), encoding="utf-8")
                        destino.write_text(corpo.rstrip() + "\n", encoding="utf-8")
                    else:
                        destino.write_text(saida, encoding="utf-8")
                        (paper_dir / base.REVISAO).write_text(saida, encoding="utf-8")
                else:
                    destino.write_text(saida, encoding="utf-8")
                    manuscrito = (paper_dir / base.MANUSCRITO)
                    if manuscrito.exists():
                        texto, correcoes = analysis.corrigir_auto(manuscrito.read_text(encoding="utf-8"))
                        (paper_dir / base.REVISAO).write_text(
                            "## Correções automáticas aplicadas\n\n" +
                            ("\n".join(f"- {c}" for c in correcoes) or "- nenhuma") +
                            "\n\n_O restante segue o cartão do Revisor no manuscrito._\n", encoding="utf-8")
                        manuscrito.write_text(texto, encoding="utf-8")
            else:
                saida = _executar(rolo, ctx, cfg, tem_llm)
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text(saida, encoding="utf-8")
            dur = round(time.time() - inicio, 1)
            consola.print(f"    [dim]concluído em {dur}s[/dim]")
            log({"fase": rolo_id, "status": status, "segundos": dur, "em": time.strftime("%Y-%m-%dT%H:%M:%S")})
            resultados.append({"rolo": rolo_id, "status": status})
        except Exception as e:  # noqa: BLE001 — uma etapa não derruba a pipeline
            dur = round(time.time() - inicio, 1)
            consola.print(f"    [red]erro: {e.__class__.__name__}: {e} → esqueleto gerado[/red]")
            try:
                destino.parent.mkdir(parents=True, exist_ok=True)
                if not destino.is_dir():
                    destino.write_text(base.esqueleto(rolo, dict(ctx, **cfg_visistent(cfg_visivel, erro=str(e)))), encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
            log({"fase": rolo_id, "status": f"erro→esqueleto: {e}", "segundos": dur})
            resultados.append({"rolo": rolo_id, "status": f"erro→esqueleto"})
    _montar_final(paper_dir, cfg)
    return {"ok": True, "resultados": resultados, "paper_dir": str(paper_dir), "tem_llm": tem_llm}


def cfg_visistent(visivel: dict, erro: str) -> dict:
    d = dict(visivel)
    d["erro"] = erro
    return d


def _montar_final(paper_dir: Path, cfg: dict) -> None:
    paper_dir = Path(paper_dir)
    candidato = paper_dir / base.MANUSCRITO
    if not candidato.exists():
        unido = base._unir_secoes(paper_dir)
        if unido:
            candidato.write_text(unido, encoding="utf-8")
    final = candidato.read_text(encoding="utf-8") if candidato.exists() else "# Paper em construção\n"
    if not re.search(r"^##\s+(Referências|Referencias|Bibliografia)\s*$", final, flags=re.M):
        fontes_arq = paper_dir / base.FONTES
        if fontes_arq.exists():
            try:
                fontes = json.loads(fontes_arq.read_text(encoding="utf-8"))
                refs = ["", "## Referências", ""]
                for f in fontes:
                    data = str(f.get("data") or "")[:10]
                    refs.append(f"[{f.get('id', '?')}] {f.get('titulo', '')} — <{f.get('url', '')}> {('('+data+')') if data else ''}".rstrip())
                final += "\n" + "\n".join(refs) + "\n"
            except json.JSONDecodeError:
                pass
    (paper_dir / base.PAPER).write_text(final, encoding="utf-8")
    plano = _ler_plano(paper_dir)
    if _plano_eh_exemplo(plano):
        plano = {}
    meta_intake = _meta_intake(paper_dir)
    m_titulo = re.search(r"^#\s+(.+)$", final, flags=re.M)
    h1 = m_titulo.group(1).strip() if m_titulo else None
    if h1 and (h1.startswith("\U0001F3AB") or h1.startswith("Cart")):
        h1 = None  # H1 é só o cartão do agente, não um título
    meta = {
        "titulo": plano.get("titulo") or meta_intake.get("assunto") or h1 or paper_dir.name,
        "resumo": plano.get("resumo", ""),
        "palavras_chave": plano.get("palavras_chave", []),
        "autor": cfg.get("autor", "Equipe Papo Pepper"),
        "data": date.today().isoformat(),
        "assunto": meta_intake.get("assunto", ""),
        "versao": __import__("papo_pepper").__version__,
        "pipeline": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (paper_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def meta(paper_dir: str | Path) -> dict:
    caminho = Path(paper_dir) / "meta.json"
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def estado(paper_dir: str | Path) -> list[tuple[str, str, str]]:
    paper_dir = Path(paper_dir)
    esperados = [(r.emoji + " " + r.nome, r.artefato) for r in base.EQUIPE]
    linhas: list[tuple[str, str, str]] = []
    for nome, artefato in esperados:
        caminho = paper_dir / artefato
        if caminho.is_dir():
            n = len(list(caminho.glob("*.md")))
            linhas.append((nome, artefato, f"✔ {n} seções" if n else "vazio"))
        elif caminho.exists():
            corpo = caminho.read_text(encoding="utf-8")[:300]
            linhas.append((nome, artefato, "◐ esqueleto (completar)" if MARCA_ESQUELETO in corpo else "✔ completo"))
        else:
            linhas.append((nome, artefato, "✘ ausente"))
    for extra in (base.PAPER, "meta.json", "paper.pdf", "paper.docx", "paper.html", "referencias.bib"):
        if (paper_dir / extra).exists():
            linhas.append(("📦 export", extra, "✔ gerado"))
    return linhas
