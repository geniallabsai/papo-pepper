"""Definição dos papéis da equipe + execução de etapas (LLM ou esqueleto)."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import llm

INTAKE = "00_intake.md"
PLANO = "01_plano.md"
FONTES = "02_fontes.json"
FONTES_NOTAS = "02_notas_pesquisa.md"
MAPA = "03_mapa_informacional.md"
SECOES_DIR = "04_secoes"
CETICO = "05_relatorio_cetico.md"
DESAFIOS = "06_desafios.md"
VALIDACAO = "07_validacao.md"
VEREDITO = "08_veredito.md"
FIGURAS = "09_figuras.md"
MANUSCRITO = "10_manuscrito_final.md"
REVISAO = "11_revisao.md"
PAPER = "12_paper.md"
PERFIL_REPO = "00_perfil_repositorio.json"
MATERIAL = "00_material_original.md"
ANALISE_MATERIAL = "02_analise_material.md"
DOC_CODIGO = "04_documento_codigo.md"

MARCA_ESQUELETO = "<!-- papo-pepper: esqueleto"


@dataclass(frozen=True)
class Rolo:
    id: str
    nome: str
    emoji: str
    artefato: str
    template: str
    sistema: str
    instrucao: str
    saida_json: bool = False
    depende_de: tuple[str, ...] = ()


EQUIPE: list[Rolo] = [
    Rolo("editor", "Editor-Chefe", "🧭", PLANO, "editor",
         "Você é o Editor-Chefe da equipe Papo Pepper. Define escopo, público e a arquitetura editorial do paper antes de qualquer pesquisa.",
         "Plano do paper (JSON fechado + racional editorial)."),
    Rolo("pesquisador", "Pesquisador Profundo", "🔎", FONTES_NOTAS, "pesquisador",
         "Você é o Pesquisador Profundo da equipe Papo Pepper. Caça evidências primárias, papers, dados e benchmarks; transforma matéria-bruta em fontes citáveis com nível de confiabilidade.",
         "Fontes finais (JSON) + notas de pesquisa + lacunas."),
    Rolo("cientista", "Cientista da Informação", "🗂️", MAPA, "cientista",
         "Você é o Cientista da Informação da equipe Papo Pepper. Classifica, hierarquiza e conecta as fontes; decide a estratégia de evidência que o paper vai seguir.",
         "Mapa informacional: taxonomia, mapa de fontes, pirâmide de evidência, numeração final."),
    Rolo("especialista", "Especialista de Domínio", "🎓️", SECOES_DIR + "/", "especialista",
         "Você é o Especialista de Domínio da equipe Papo Pepper. Escreve as seções técnicas/científicas com rigor formal, fórmulas verificadas por código e citação precisa [n].",
         "Seções profundas do manuscrito (arquivos 04_secoes/*.md)."),
    Rolo("cetico", "Cético", "🕵️", CETICO, "cetico",
         "Você é o Cético da equipe Papo Pepper. Seu trabalho é tentar DERRUBAR o paper com método, citando trechos exatos. Afirmação sem prova é presa sua.",
         "Relatório de ataques, afirmações órfãs e parecer parcial."),
    Rolo("retador", "Retador Adversarial", "⚔️", DESAFIOS, "retador",
         "Você é o Retador Adversarial da equipe Papo Pepper. Faz as perguntas mais difíceis que um revisor hostil faria e define o que contaria como resposta aceitável.",
         "Lista de desafios (com teste objetivo cada) + ranking de ameaça."),
    Rolo("validador", "Validador", "✅", VALIDACAO, "validador",
         "Você é o Validador da equipe Papo Pepper. Confere cada número, fórmula e referência contra a realidade; se não reproduz, não vale.",
         "Tabela de verificação (show your work) + contradições + sentença."),
    Rolo("juiz", "Juiz Revisor", "⚖️", VEREDITO, "juiz",
         "Você é o Juiz Revisor da equipe Papo Pepper. Última instância: lê manuscrito, ataques, desafios e validações e emite veredito ACEITO/REVISAR com pontuação por dimensão.",
         "Veredito (JSON + fundamentação).", saida_json=True),
    Rolo("diagramador", "Diagramador", "📐", FIGURAS, "diagramador",
         "Você é o Diagramador da equipe Papo Pepper. Transforma conceitos em figuras Mermaid limpas (≤12 nós, rótulos curtos) com legenda e local de inserção.",
         "Figuras mermaid + índice (09_figuras.md)."),
    Rolo("escritor", "Escritor Integrador", "✍️", MANUSCRITO, "escritor",
         "Você é o Escritor Integrador da equipe Papo Pepper. Junta seções, respostas aos desafios e correções em um paper final coeso — sem gordura, sem promessa vazia.",
         "Manuscrito final completo (título → referências)."),
    Rolo("revisor", "Revisor Final", "🔍", REVISAO, "revisor",
         "Você é o Revisor Final da equipe Papo Pepper. Só forma, zero conteúdo: gramática, terminologia, ritmo, formatação. Nada de cortar argumento.",
         "Texto revisado completo + changelog de revisão."),
    Rolo("documentalista", "Documentalista de Código", "📚", DOC_CODIGO, "documentalista",
         "Você é o Documentalista de Código da equipe Papo Pepper. Lê o perfil de um repositório e produz a documentação técnica que ele merece.",
         "Documento técnico do código + perguntas ao desenvolvedor."),
]

POR_ID = {r.id: r for r in EQUIPE}

PIPELINE_PADRAO = ["editor", "pesquisador", "cientista", "especialista", "cetico", "retador",
                   "validador", "juiz", "diagramador", "escritor", "revisor"]
PIPELINE_REPO = ["editor", "documentalista", "pesquisador", "cientista", "especialista", "cetico",
                 "retador", "validador", "juiz", "diagramador", "escritor", "revisor"]


def carregar_template(id_rolo: str) -> str:
    caminho = Path(__file__).resolve().parent.parent / "prompts" / f"{id_rolo}.md"
    return caminho.read_text(encoding="utf-8")


def substituir(template: str, ctx: dict[str, Any]) -> str:
    """Substitui {{chave}} por valor; chaves ausentes viram texto vazio."""
    texto = template
    for chave, valor in ctx.items():
        if valor is not None:
            texto = texto.replace("{{" + chave + "}}", str(valor))
    return re.sub(r"\{\{\w+\}\}", "", texto)


def ler_artefato(caminho: Path, max_chars: int = 16000) -> str:
    if not caminho.exists():
        return ""
    texto = caminho.read_text(encoding="utf-8")
    return texto[:max_chars] + "\n… [truncado]" if len(texto) > max_chars else texto


def _carregar_fontes(paper_dir: Path) -> list[dict]:
    arq = paper_dir / FONTES
    if arq.exists():
        try:
            return json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def _unir_secoes(paper_dir: Path) -> str:
    pasta = paper_dir / SECOES_DIR
    if not pasta.is_dir():
        return ""
    blocos = [a.read_text(encoding="utf-8") for a in sorted(pasta.glob("*.md"))]
    return "\n\n---\n\n".join(blocos)[:24000]


def contextuar(paper_dir: Path, extra: dict | None = None) -> dict[str, Any]:
    """Monta o contexto de entrada a partir dos artefatos existentes no diretório do paper."""
    ctx: dict[str, Any] = {
        "intake": ler_artefato(paper_dir / INTAKE),
        "plano": ler_artefato(paper_dir / PLANO),
        "material": ler_artefato(paper_dir / MATERIAL),
        "analise_material": ler_artefato(paper_dir / ANALISE_MATERIAL),
        "material_original": ler_artefato(paper_dir / MATERIAL, max_chars=30000),
        "fontes": json.dumps(_carregar_fontes(paper_dir), ensure_ascii=False, indent=1)[:14000],
        "notas_pesquisa": ler_artefato(paper_dir / FONTES_NOTAS),
        "mapa_informacional": ler_artefato(paper_dir / MAPA),
        "secoes": _unir_secoes(paper_dir),
        "documento_codigo": ler_artefato(paper_dir / DOC_CODIGO),
        "perfil_repositorio": (paper_dir / PERFIL_REPO).read_text(encoding="utf-8")
        if (paper_dir / PERFIL_REPO).exists() else "",
        "manuscrito": ler_artefato(paper_dir / MANUSCRITO) or _unir_secoes(paper_dir),
        "cetico": ler_artefato(paper_dir / CETICO),
        "desafios": ler_artefato(paper_dir / DESAFIOS),
        "validacao": ler_artefato(paper_dir / VALIDACAO),
        "veredito": ler_artefato(paper_dir / VEREDITO),
    }
    ctx.update(extra or {})
    return ctx


def executar(rolo: Rolo, ctx: dict[str, Any], cfg: dict, *, ao_tokeno=None) -> str:
    template = carregar_template(rolo.id)
    mensagem = [{"role": "user", "content": substituir(template, ctx)}]
    saida = llm.chat(rolo.sistema, mensagem, cfg=cfg, ao_tokeno=ao_tokeno)
    if not saida.strip():
        raise llm.LLMError(f"{rolo.nome} devolveu resposta vazia.")
    return saida


def esqueleto(rolo: Rolo, ctx: dict[str, Any]) -> str:
    corpo = substituir(carregar_template(rolo.id), ctx)
    cab = (
        f"<!-- {MARCA_ESQUELETO} -->\n"
        f"# 🎫 Cartão do Agente — {rolo.emoji} {rolo.nome}\n\n"
        f"> {rolo.sistema}\n>\n"
        f"> **Produto esperado:** {rolo.instrucao}\n>\n"
        f"> **Como continuar:** conecte um LLM (`papo-pepper models` explica) e rode a etapa "
        f"`papo-pepper etapa {rolo.id} --paper <dir>`, ou complete este artefato seguindo as "
        f"instruções abaixo. A etapa seguinte da pipeline lê este arquivo — respeite o formato de saída.\n\n"
        f"---\n\n"
    )
    return cab + corpo
