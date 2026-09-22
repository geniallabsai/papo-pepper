"""Configuração do Papo Pepper: defaults < config.yaml < variáveis de ambiente PAPER_*."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DIR_CFG = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "papo-pepper"
ARQ_CFG = DIR_CFG / "config.yaml"

PADROES: dict[str, Any] = {
    "provider": None,          # anthropic | openai | openrouter | ollama | custom | off
    "model": None,             # ex.: claude-sonnet-4-5, gpt-5, llama3.3:70b
    "base_url": None,
    "api_key": None,
    "autor": "Equipe Papo Pepper",
    "idioma": "pt-BR",
    "estilo_citacao": "apa",   # apa | ieee | vancouver | abnt | livre
    "formato_preferido": "pdf",  # pdf | word
    "profundidade": "padrao",   # padrao | maxima
    "diretorio_papers": "papers",
    "temperatura": 0.4,
    "max_tokens": 8192,
}

_AMB = {
    "provider": "PAPER_PROVIDER",
    "model": "PAPER_MODEL",
    "base_url": "PAPER_BASE_URL",
    "api_key": "PAPER_API_KEY",
    "autor": "PAPER_AUTOR",
    "idioma": "PAPER_IDIOMA",
    "estilo_citacao": "PAPER_CITACAO",
    "formato_preferido": "PAPER_FORMATO",
    "profundidade": "PAPER_PROFUNDIDADE",
    "diretorio_papers": "PAPER_DIR",
}


def carregar() -> dict[str, Any]:
    cfg = dict(PADROES)
    if ARQ_CFG.exists():
        try:
            dados = yaml.safe_load(ARQ_CFG.read_text(encoding="utf-8")) or {}
            cfg.update({k: v for k, v in dados.items() if k in PADROES})
        except yaml.YAMLError:
            pass
    for chave, env in _AMB.items():
        if os.getenv(env):
            cfg[chave] = os.environ[env]
    return cfg


def salvar(parcial: dict[str, Any]) -> Path:
    atual: dict[str, Any] = {}
    if ARQ_CFG.exists():
        atual = yaml.safe_load(ARQ_CFG.read_text(encoding="utf-8")) or {}
    atual.update(parcial)
    ARQ_CFG.parent.mkdir(parents=True, exist_ok=True)
    ARQ_CFG.write_text(yaml.safe_dump(atual, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return ARQ_CFG


def descrever(cfg: dict) -> list[tuple[str, str]]:
    """Linha a linha para exibição: provedor detectado + opções ativas."""
    from . import llm

    info = llm.detectar(cfg)
    linhas: list[tuple[str, str]] = []
    if info:
        chave = info["chave"]
        mascarado = (chave[:6] + "…" + chave[-4:]) if len(chave) > 12 else chave
        linhas += [
            ("Provedor", info["provedor"]),
            ("Modelo", info["modelo"]),
            ("Base URL", info["base"]),
            ("Chave API", mascarado),
        ]
    else:
        linhas.append(("Provedor", "nenhum — modo esqueleto (um agente externo completa as etapas)"))
    for k in ("autor", "idioma", "estilo_citacao", "formato_preferido", "profundidade", "diretorio_papers"):
        linhas.append((k, str(cfg.get(k))))
    return linhas
