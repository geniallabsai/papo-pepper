"""CLI do Papo Pepper."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from . import __version__, analysis, intake as intake_mod, llm, orchestrator
from .agents import base
from .config import carregar as carregar_cfg, descrever as descrever_cfg
from .console import banner, consola
from .exporter import exportar_paper


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="papo-pepper")
def main() -> None:
    """🌶️ Papo Pepper — equipe multi-agente que transforma qualquer assunto em paper profundo.

    Assunto, entrevista, áudio, texto existente ou repositório de código entram;
    paper estruturado (PDF/Word/HTML/BibTeX) sai — revisado por cético, retador,
    validador e juiz antes do export.
    """
    banner()


# ------------------------------------------------------------------ novo
@main.command("novo")
@click.argument("assunto")
@click.option("--tipo", default=None, help="tecnico | cientifico | pedagogico | profissional")
@click.option("--publico", default=None, help="público-alvo em poucas palavras")
@click.option("--entrevista", is_flag=True, help="roda a entrevista conversacional antes da pipeline")
@click.option("--audio", type=click.Path(exists=True), default=None, help="áudio ou .txt de transcrição para extrair o conhecimento")
@click.option("--material", type=click.Path(exists=True), default=None, help="texto existente (.md/.txt/.docx/.html) para analisar e melhorar")
@click.option("--repo", "repo_dir", type=click.Path(exits=True) if False else click.Path(exists=True), default=None,
              help="repositório a documentar e transformar em paper técnico")
@click.option("--desde", type=click.Choice([r.id for r in base.EQUIPE]), default=None, help="inicia a pipeline nesta etapa")
@click.option("--ate", type=click.Choice([r.id for r in base.EQUIPE]), default=None, help="termina a pipeline nesta etapa")
@click.option("--forcar", is_flag=True, help="reexecuta etapas já concluídas")
@click.option("--sem-exportar", is_flag=True, help="não gera PDF/Word/HTML ao final")
@click.option("--formatos", default=None, help="ex.: html,word,pdf,bib (padrão: todos)")
@click.option("--diretorio", default=None, help="diretório raiz dos papers")
@click.option("--modelo", default=None, help="modelo LLM p/ esta execução (ex.: claude-opus-4-5, gpt-5)")
def novo(assunto, tipo, publico, entrevista, audio, material, repo_dir, desde, ate, forcar,
         sem_exportar, formatos, diretorio, modelo):
    """Cria um paper: intake → 11 fases da equipe → exportação."""
    cfg = carregar_cfg()
    if modelo:
        cfg["model"] = modelo
    if not llm.disponivel(cfg):
        consola.print("[yellow]Nenhum LLM detectado → modo ESQUELETO (cartões de agente). Veja "
                      "[bold]papo-pepper models[/bold] para configurar, ou deixe um agente "
                      "(Claude Code/Codex/OpenClaw/Hermes) completar as etapas seguindo skills/.[/yellow]")
    paper_dir = orchestrator.criar_papel(diretorio or cfg.get("diretorio_papers"), assunto, cfg)
    consola.print(f"Paper: [bold]{paper_dir}[/bold]")

    modo = None
    # repositório
    if repo_dir:
        modo = "repo"
        consola.print("[bold]Analisando repositório…[/bold]")
        perfil = analysis.analisar_repositorio(Path(repo_dir))
        (paper_dir / base.PERFIL_REPO).write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")
        (paper_dir / "00_perfil_repositorio.md").write_text(analysis.perfil_para_markdown(perfil), encoding="utf-8")
        langs = ", ".join(f"{k} ({v})" for k, v in perfil["linguagens"].items())
        consola.print(f"  {perfil['arquivos_fonte']} arquivos · {langs} · testes: {perfil['testes_arquivos']}")
    # material existente
    if material:
        texto = analysis.ler_documento(Path(material))
        (paper_dir / base.MATERIAL).write_text(texto, encoding="utf-8")
        (paper_dir / base.ANALISE_MATERIAL).write_text(analysis.relatorio_texto(texto, cfg), encoding="utf-8")
        consola.print(f"Material ({len(texto)} caracteres) salvo + análise heurística pronta.")
    # áudio / transcrição
    transcricao = None
    if audio:
        consola.print("[bold]Transcrevendo…[/bold]")
        transcricao = intake_mod.transcrever(Path(audio))
        (paper_dir / "00_transcricao.txt").write_text(transcricao, encoding="utf-8")
    extra_json = None
    if transcricao:
        extra_json = intake_mod.extrair_da_transcricao(transcricao, cfg)
    # entrevista
    respostas: dict[str, str]
    if entrevista:
        pre = {"assunto": assunto, "publico": publico or "", "tipo": tipo or ""}
        if extra_json:
            pre.update({
                "assunto": extra_json.get("assunto") or assunto,
                "publico": extra_json.get("publico_sugerido") or "",
                "tipo": extra_json.get("tipo_sugerido") or "",
                "tom": extra_json.get("tom") or "",
            })
        respostas = intake_mod.entrevista(consola, cfg, pre=pre)
        tipo = tipo or respostas.get("tipo")
        publico = publico or respostas.get("publico")
        profundidade = respostas.get("profundidade")
        if profundidade:
            cfg["profundidade"] = "maxima" if "maxima" in profundidade.lower() else "padrao"
        citacao = respostas.get("citacao")
        if citacao and citacao != "nenhuma":
            cfg["estilo_citacao"] = citacao[:8]
    else:
        respostas = {k: "" for k, _ in intake_mod.QUESTOES}
        respostas.update({"assunto": assunto, "tipo": tipo or "tecnico", "publico": publico or ""})
    intake_mod.gravar_intake(paper_dir, respostas, cfg, modo="entrevista" if entrevista else "assunto-livre",
                             transcricao=transcricao, extra_json=extra_json)

    resumo = orchestrator.rodar(paper_dir, cfg, modo=modo, desde=desde, ate=ate, forcar=forcar)
    if not sem_exportar:
        fmt = [f.strip().lower() for f in formatos.split(",")] if formatos else None
        consola.print("\n[bold]Exportando…[/bold]")
        gerados = exportar_paper(paper_dir, formatos=fmt)
        for g in gerados:
            consola.print(f"  [green]✔[/] [bold]{g}[/bold]")
    meta = orchestrator.meta(paper_dir)
    tabela = _tabela_estado(paper_dir)
    consola.print(tabela)
    consola.print(Panel.fit(
        f"[bold]{meta.get('titulo', 'Paper')!s}[/bold]\n"
        f"Pasta: [dim]{paper_dir}[/dim]\n\n"
        "Próximos passos:\n"
        "  • Abrir [bold]paper.pdf[/bold] / [bold]paper.docx[/bold] quando prontos\n"
        "  • Refinar uma etapa: [bold]papo-pepper etapa <rolo> --paper <dir>[/bold]\n"
        "  • Com um LLM conectado e --forcar, as etapas voltam a rodar automaticamente",
        title="🌶️ Papo Pepper", border_style="red3"))


def _tabela_estado(paper_dir: Path) -> Table:
    t = Table(title="Estado da pipeline", show_lines=False)
    t.add_column("papel", style="cyan")
    t.add_column("artefato", style="dim")
    t.add_column("status")
    for nome, artefato, status in orchestrator.estado(paper_dir):
        t.add_row(nome, artefato, status)
    return t


# ------------------------------------------------------------------ estado
@main.command("estado")
@click.argument("paper", type=click.Path(exists=True))
def estado(paper: str) -> None:
    """Mostra o estado dos artefatos de um paper."""
    consola.print(_tabela_estado(Path(paper)))


# ------------------------------------------------------------------ etapa
@main.command("etapa")
@click.argument("rolo_id", type=click.Choice(list(base.POR_ID)))
@click.option("--paper", required=True, type=click.Path(exists=True), help="diretório do paper")
@click.option("--secao", default=None, help="apenas para especialista: título da seção a (re)escrever")
@click.option("--modelo", default=None, help="modelo LLM p/ esta etapa")
def etapa(rolo_id: str, paper: str, secao: str | None, modelo: str | None) -> None:
    """Reexecuta UMA etapa (refinar com outro modelo ou fechar um esqueleto)."""
    cfg = carregar_cfg()
    if modelo:
        cfg["model"] = modelo
    if not llm.disponivel(cfg):
        raise SystemExit("Nenhum LLM configurado — conecte um provedor (papo-pepper models) para executar etapas.")
    from . import llm as _llm
    from .agents.base import contextuar, POR_ID, SECOES_DIR
    from .orchestrator import slugify, _secoes_do_plano, _ler_plano

    paper_dir = Path(paper)
    rolo = POR_ID[rolo_id]
    ctx = contextuar(paper_dir)
    meta = orchestrator.meta(paper_dir)
    ctx.update({"assunto": meta.get("assunto", ""), "autor": meta.get("autor", ""), "data": meta.get("data", "")})
    destino = paper_dir / rolo.artefato
    consola.print(f"[bold]{rolo.emoji} {rolo.nome}[/] → {rolo.artefato}")
    if rolo_id == "especialista":
        plano = _ler_plano(paper_dir)
        secoes = _secoes_do_plano(plano)
        if secao:
            secoes = [s for s in secoes if secao.lower() in str(s.get("titulo", "")).lower()]
            if not secoes:
                raise SystemExit(f"Seção '{secao}' não encontrada no plano.")
        for n_sec, sec in enumerate(secoes, 1):
            ctx_sec = dict(ctx)
            ctx_sec["secao_titulo"] = str(sec.get("titulo"))
            ctx_sec["secao_foco"] = str(sec.get("foco", ""))
            ctx_sec["palavras_alvo"] = "1200"
            saida = base.executar(rolo, ctx_sec, cfg)
            (paper_dir / SECOES_DIR).mkdir(exist_ok=True)
            nome_sec = f"{n_sec:02d}_{slugify(str(sec.get('titulo', '')).split(' ', 1)[-1])}.md"
            (paper_dir / SECOES_DIR / nome_sec).write_text(saida, encoding="utf-8")
            consola.print(f"  ✔ {nome_sec}")
    else:
        saida = base.executar(rolo, ctx, cfg)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(saida, encoding="utf-8")
        consola.print(f"  ✔ {destino}")
    if rolo_id in ("cetico", "retador", "validador", "juiz", "diagramador"):
        try:
            exportar_paper(paper_dir, formatos=["html"])
            consola.print("  ✔ paper.html atualizado")
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------------ exportar
@main.command("exportar")
@click.argument("paper", type=click.Path(exists=True))
@click.option("--formatos", default=None, help="html,word,pdf,bib (padrão: todos)")
def exportar(paper: str, formatos: str | None) -> None:
    """Exporta um paper existente (12_paper.md) para HTML/Word/PDF/BibTeX."""
    fmt = [f.strip().lower() for f in formatos.split(",")] if formatos else None
    gerados = exportar_paper(Path(paper), formatos=fmt)
    for g in gerados:
        consola.print(f"  [green]✔[/] [bold]{g}[/bold]")


# ------------------------------------------------------------------ analisar
@main.command("analisar")
@click.argument("caminho", type=click.Path(exists=True))
@click.option("--diretorio", default=None, help="diretório raiz dos papers")
@click.option("--copiar-docs/--sem-copiar-docs", default=False,
              help="(repo) copiar a documentação gerada para docs/ do projeto")
def analisar(caminho: str, diretorio: str | None, copiar_docs: bool) -> None:
    """Analisa TEXTO EXISTENTE (relatório + melhorias) ou REPOSITÓRIO (perfil + paper técnico)."""
    p = Path(caminho)
    tp = analysis.detectar_tipo(p)
    cfg = carregar_cfg()
    if tp == "repo":
        consola.print(f"[bold]Modo repositório:[/bold] {p.resolve()}")
        perfil = analysis.analisar_repositorio(p)
        assunto = f"Análise técnica e documentação de {perfil['nome']}"
        paper_dir = orchestrator.criar_papel(diretorio or cfg.get("diretorio_papers"), assunto, cfg)
        (paper_dir / base.PERFIL_REPO).write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")
        (paper_dir / "00_perfil_repositorio.md").write_text(analysis.perfil_para_markdown(perfil), encoding="utf-8")
        intake_mod.stub_intake(paper_dir, assunto, tipo="tecnico", cfg=cfg)
        if not llm.disponivel(cfg):
            consola.print("[yellow]Sem LLM → esqueletos (cartões de agente) para o modo repo.[/yellow]")
        resumo = orchestrator.rodar(paper_dir, cfg, modo="repo")
        if copiar_docs:
            doc = paper_dir / base.DOC_CODIGO
            if doc.exists():
                destino_docs = p / "docs"
                destino_docs.mkdir(exist_ok=True)
                alvo = destino_docs / "papopepper-documentacao.md"
                alvo.write_text(doc.read_text(encoding="utf-8"), encoding="utf-8")
                consola.print(f"  [green]✔[/] documentação copiada para {alvo}")
        gerados = exportar_paper(paper_dir)
        for g in gerados:
            consola.print(f"  [green]✔[/] [bold]{g}[/bold]")
    elif tp == "texto":
        texto = analysis.ler_documento(p)
        slug = orchestrator.slugify(p.stem)
        destino = Path(diretorio or cfg.get("diretorio_papers", "papers")) / f"analise-{slug}"
        destino.mkdir(parents=True, exist_ok=True)
        relatorio = analysis.relatorio_texto(texto, cfg)
        (destino / "relatorio_analise.md").write_text(relatorio, encoding="utf-8")
        consola.print(f"  [green]✔[/] relatorio_analise.md em {destino}")
        melhorado = False
        if llm.disponivel(cfg):
            try:
                from .agents.base import carregar_template, substituir
                template = carregar_template("melhorar")
                saida = llm.chat(
                    "Você é o Melhorador de Material da equipe Papo Pepper.",
                    [{"role": "user", "content": substituir(template, {"material_original": texto[:30000], "analise_material": relatorio})}],
                    cfg=cfg)
                (destino / "material_melhorado.md").write_text(saida, encoding="utf-8")
                melhorado = True
                consola.print("  [green]✔[/] material_melhorado.md")
            except Exception as e:  # noqa: BLE001
                consola.print(f"  [yellow]melhoria com LLM falhou ({e.__class__.__name__}); seguindo só com heurísticas.[/yellow]")
        if not melhorado:
            texto_fix, correcoes = analysis.corrigir_auto(texto)
            (destino / "material_corrigido_auto.md").write_text(texto_fix, encoding="utf-8")
            (destino / "correcoes_auto.md").write_text(
                "# Correções automáticas\n\n" + ("\n".join(f"- {c}" for c in correcoes) or "- nenhuma") + "\n",
                encoding="utf-8")
            consola.print("  [green]✔[/] material_corrigido_auto.md (sem LLM — correções automáticas)")
    else:
        raise SystemExit(f"Formato não suportado: use .md .txt .rst .docx .html ou um diretório de projeto ({caminho}).")


# ------------------------------------------------------------------ modelos
@main.command("models")
def models() -> None:
    """Mostra provedores configurados + curadoria dos modelos mais recentes recomendados."""
    from . import models as cur

    cfg = carregar_cfg()
    t1 = Table(title="Configuração atual", title_style="red3")
    t1.add_column("chave", style="cyan")
    t1.add_column("valor")
    for k, v in descrever_cfg(cfg):
        t1.add_row(k, v)
    consola.print(t1)
    consola.print(Panel("CURADORIA DE MODELOS (recomendação: SEMPRE os mais recentes no seu provedor)",
                        title=f"🌶️ referência {cur.REFERENCIA}", border_style="red3"))
    for linha in cur.linhas_curados()[1:]:
        consola.print(linha)
    consola.print("\n[bold]Estratégia por fase:[/bold]")
    for linha in cur.linhas_estrategia():
        consola.print(linha)
    consola.print("\n[bold]Dicas:[/bold]")
    for d in cur.DICAS:
        consola.print(f"  • {d}")


# ------------------------------------------------------------------ setup
@main.command("setup")
@click.option("--alvo", default=None, help="codex | claude | openclaw | hermes | generico")
@click.option("--completo", is_flag=True, help="instala extras pdf+audio+math")
@click.option("--mcp", "com_mcp", is_flag=True, help="registra o servidor MCP nos agentes compatíveis")
def setup(alvo: str | None, completo: bool, com_mcp: bool) -> None:
    """Reinstala skills/adapters nos agentes detectados e verifica o ambiente."""
    if completo:
        consola.print("[bold]Instalando extras (pdf/audio/math)…[/bold]")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[pdf,audio,math]"],
                           capture_output=True, text=True)
        consola.print(f"  pip: {'ok' if r.returncode == 0 else r.stderr[-300:]}")
    from . import installers
    resumo = installers.instalar(alvo=alvo, com_mcp=com_mcp)
    t = Table(title="Adapters instalados", title_style="red3")
    t.add_column("alvo", style="cyan")
    t.add_column("onde/resultado")
    for k, v in resumo.items():
        t.add_row(k, str(v))
    consola.print(t)
    consola.print("[dim]Verifique o provedor com 'papo-pepper models' antes de criar papers.[/dim]")


# ------------------------------------------------------------------ config
@main.command("config")
@click.argument("pares", nargs=-1)
def config(pares) -> None:
    """Mostra a config ou configura pares chave=valor (ex.: config autor "Seu Nome")."""
    cfg = carregar_cfg()
    if pares:
        if len(pares) % 2 != 0:
            raise SystemExit("Uso: papo-pepper config chave1 valor1 [chave2 valor2 ...]")
        dados = {}
        for i in range(0, len(pares), 2):
            dados[pares[i]] = pares[i + 1]
        caminho = __import__("papo_pepper.config", fromlist=["salvar"]).salvar(dados)
        consola.print(f"[green]✔ salvo em {caminho}[/green]")
    else:
        t = Table(title="Configuração efetiva", title_style="red3")
        t.add_column("chave", style="cyan")
        t.add_column("valor")
        for k, v in descrever_cfg(cfg):
            t.add_row(k, v)
        consola.print(t)
        from .config import ARQ_CFG
        consola.print(f"[dim]arquivo: {ARQ_CFG}[/dim]")


if __name__ == "__main__":
    main()
