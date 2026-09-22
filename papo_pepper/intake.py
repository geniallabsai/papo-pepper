"""Entrada de conhecimento: entrevista conversacional, áudio (transcrição) e extração por LLM."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import yaml

QUESTOES: list[tuple[str, str]] = [
    ("assunto", "Qual é o assunto central do paper? (uma ou duas frases)"),
    ("publico", "Para quem é? (leigos, técnicos, academia, gestores...)"),
    ("tipo", "Tipo: tecnico / cientifico / pedagogico / profissional [padrão: tecnico]?"),
    ("objetivo", "O que o leitor precisa entender ou conseguir fazer ao terminar?"),
    ("profundidade", "Profundidade: padrao (~10 páginas) / maxima (monografia) [padrão: padrao]?"),
    ("dados", "Você tem dados, experimentos, resultados ou um repositório por trás? Descreva ou aponte arquivos."),
    ("objecoes", "Quais objeções ou posições contrárias você já conhece sobre o tema?"),
    ("tom", "Tom: rigoroso-academico / tecnico-claro / executivo [padrão: tecnico-claro]?"),
    ("citacao", "Estilo de citação: apa / ieee / vancouver / abnt / livre [padrão: apa]?"),
    ("restricoes", "Restrições de formato, tamanho, prazo? (ou 'nenhuma')"),
]


def transcrever(audio: Path, modelo_whisper: str = "small") -> str:
    """Áudio → texto. Aceita .txt/.md/.srt diretamente (transcrição manual)."""
    audio = Path(audio)
    if audio.suffix.lower() in {".txt", ".md", ".srt"}:
        return audio.read_text(encoding="utf-8")
    try:
        from faster_whisper import WhisperModel
        modelo = WhisperModel(modelo_whisper, device="cpu", compute_type="int8")
        segs, _ = modelo.transcribe(str(audio), language="pt")
        return " ".join(s.text.strip() for s in segs)
    except ImportError:
        pass
    try:
        import whisper  # type: ignore
        w = whisper.load_model(modelo_whisper)
        r = w.transcribe(str(audio), fp16=False)
        return str(r["text"]).strip()
    except ImportError:
        raise RuntimeError(
            "Para transcrever áudio instale um backend: pip install 'papo-pepper[audio]' "
            "(faster-whisper) — ou salve a transcrição em .txt e passe o arquivo."
        ) from None


def extrair_da_transcricao(transcricao: str, cfg: dict) -> dict:
    """LLM extrai do bruto da conversa o que o paper vai precisar. Sem LLM: {}."""
    from . import llm
    from .agents.base import carregar_template, substituir

    if not llm.disponivel(cfg):
        return {}
    try:
        template = carregar_template("extracao-intake")
        ctx = {"assunto": "", "transcricao": transcricao[:24000]}
        sistema = "Você extrai estrutura de entrevistas para a equipe Papo Pepper. Devolve somente JSON."
        dado = llm.chat_json(sistema, [{"role": "user", "content": substituir(template, ctx)}], cfg=cfg)
        return dado if isinstance(dado, dict) else {}
    except llm.LLMError:
        return {}


def entrevista(console, cfg: dict, pre: dict | None = None) -> dict:
    """Loop conversacional: pergunta o que ainda não sabemos; aceita pré-preenchimento."""
    from rich.prompt import Prompt

    pre = dict(pre or {})
    respostas: dict[str, str] = {}
    for chave, pergunta in QUESTOES:
        valor_pre = str(pre.get(chave) or "").strip()
        if valor_pre:
            respostas[chave] = valor_pre
            console.print(f"[dim]?[/] {pergunta} → [green]{valor_pre[:80]}[/green]")
            continue
        console.print(f"\n[bold cyan]?[/] [bold]{pergunta}[/]")
        try:
            valor = Prompt.ask(default="", show_default=False)
        except (EOFError, KeyboardInterrupt):
            valor = ""
        respostas[chave] = valor.strip()
    return respostas


def _meta_yaml(respostas: dict, cfg: dict, modo: str, transcricao: bool) -> str:
    dados = {
        "data": date.today().isoformat(),
        "modo": modo,
        "audio": transcricao,
        "idioma": cfg.get("idioma"),
        **{k: v for k, v in respostas.items() if v},
    }
    return yaml.safe_dump(dados, allow_unicode=True, sort_keys=False).strip()


def gravar_intake(paper_dir: Path, respostas: dict, cfg: dict, *, modo: str = "entrevista",
                  transcricao: str | None = None, extra_json: dict | None = None) -> Path:
    paper_dir = Path(paper_dir)
    linhas = [
        "# Intake — Papo Pepper",
        "",
        f"- **Data:** {date.today().isoformat()}",
        f"- **Modo:** {modo}" + (" · com transcrição de áudio" if transcricao else ""),
        "",
        "## Metadados",
        "",
        "```yaml",
        _meta_yaml(respostas, cfg, modo, bool(transcricao)),
        "```",
        "",
        "## Perguntas e respostas",
        "",
    ]
    for i, (chave, pergunta) in enumerate(QUESTOES, 1):
        linhas.append(f"**Q{i}.** {pergunta}")
        linhas.append("")
        linhas.append(f"> {respostas.get(chave, '—')}")
        linhas.append("")
    if extra_json:
        linhas += ["## Afirmativas extraídas (seed do paper)", ""]
        for campo in ("afirmacoes_centrais", "dados_mentionados", "objecoes_conhecidas", "lacunas"):
            itens = extra_json.get(campo) or []
            if itens:
                rotulos = {"afirmacoes_centrais": "Teses defendidas", "dados_mentionados": "Dados citados",
                           "objecoes_conhecidas": "Objeções conhecidas", "lacunas": "Lacunas apontadas"}
                linhas.append(f"### {rotulos[campo]}")
                linhas += [f"- {x}" for x in itens]
                linhas.append("")
    if transcricao:
        linhas += ["## Transcrição (áudio)", "", "> " + transcricao.replace("\n", "\n> ")[:12000]]
    caminho = paper_dir / "00_intake.md"
    caminho.write_text("\n".join(linhas), encoding="utf-8")
    return caminho


def stub_intake(paper_dir: Path, assunto: str, *, tipo: str | None = None, publico: str | None = None,
                cfg: dict) -> Path:
    respostas = {"assunto": assunto, "tipo": tipo or "tecnico", "publico": publico or ""}
    return gravar_intake(paper_dir, respostas, cfg, modo="assunto-livre")
