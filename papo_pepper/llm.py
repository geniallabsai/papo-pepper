"""Cliente LLM multi-provedor: Anthropic, endpoints compatíveis com OpenAI
(OpenAI, OpenRouter, vLLM, Groq...), Ollama local. Streaming opcional, retry em 429/5xx.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable

import httpx


class LLMError(RuntimeError):
    """Falha de configuração ou comunicação com o provedor de LLMs."""


MODELOS_PADRAO = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-5",
    "openrouter": "anthropic/claude-sonnet-4-5",
    "ollama": "llama3.3:70b",
    "custom": "",
}

BASES_PADRAO = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com",
    "openrouter": "https://openrouter.ai",
    "ollama": "http://localhost:11434",
}


def detectar(cfg: dict | None = None) -> dict | None:
    """Descobre provedor/modelo/base/chave. Retorna None se nada configurado (ou 'off')."""
    cfg = cfg or {}
    prov = str(cfg.get("provider") or os.getenv("PAPER_PROVIDER") or "").lower().strip()
    if prov in ("off", "none", "sem-llm", "nenhum"):
        return None
    base = cfg.get("base_url") or os.getenv("PAPER_BASE_URL") or ""
    chave = cfg.get("api_key") or os.getenv("PAPER_API_KEY") or ""
    modelo = cfg.get("model") or os.getenv("PAPER_MODEL") or ""

    if prov == "ollama" or os.getenv("OLLAMA") or os.getenv("OLLAMA_HOST"):
        prov = "ollama"
    if not prov:
        if base and chave:
            prov = "custom"
        elif os.getenv("ANTHROPIC_API_KEY"):
            prov = "anthropic"
        elif os.getenv("OPENROUTER_API_KEY"):
            prov = "openrouter"
        elif os.getenv("OPENAI_API_KEY"):
            prov = "openai"
        else:
            return None

    base = (base or BASES_PADRAO.get(prov, "")).rstrip("/")
    if not base:
        raise LLMError(f"Provedor \'{prov}\' precisa de base_url (PAPER_BASE_URL ou config).")
    if not chave:
        chave = (
            os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or "chave-local"
        )
    if not modelo:
        modelo = MODELOS_PADRAO.get(prov) or "gpt-5"
    return {"provedor": prov, "base": base, "chave": chave, "modelo": modelo}


def disponivel(cfg: dict | None = None) -> bool:
    return detectar(cfg) is not None


def chat(
    sistema: str,
    mensagens: list[dict[str, str]],
    *,
    cfg: dict | None = None,
    modelo: str | None = None,
    temperatura: float | None = None,
    max_tokens: int | None = None,
    timeout: float = 300.0,
    ao_tokeno: Callable[[str], None] | None = None,
) -> str:
    """Uma chamada de chat. mensagens: [{"role": "user"|"assistant", "content": "..."}]."""
    cfg = cfg or {}
    info = detectar(cfg)
    if info is None:
        raise LLMError(
            "Nenhum LLM configurado. Opções: defina ANTHROPIC_API_KEY, OPENAI_API_KEY ou "
            "OPENROUTER_API_KEY; ou PAPER_BASE_URL+PAPER_API_KEY (qualquer endpoint compatível "
            "com OpenAI); ou rode local com Ollama (OLLAMA=true). Ou use o modo sem LLM: a "
            "pipeline gera esqueletos (cartões de agente) para um agente externo completar."
        )
    prov, base, chave = info["provedor"], info["base"], info["chave"]
    modelo = modelo or info["modelo"]
    if temperatura is None:
        temperatura = float(cfg.get("temperatura", 0.4))
    if max_tokens is None:
        max_tokens = int(cfg.get("max_tokens", 8192))

    ultimo: Exception = LLMError("sem resposta do provedor")
    for tentativa in range(3):
        try:
            if prov == "anthropic":
                return _anthropic(base, chave, modelo, sistema, mensagens, temperatura, max_tokens, timeout, ao_tokeno)
            return _openai_compatible(base.rstrip("/") + "/v1", chave, modelo, sistema, mensagens, temperatura, max_tokens, timeout, ao_tokeno)
        except httpx.HTTPStatusError as e:
            ultimo = LLMError(f"HTTP {e.response.status_code} do provedor \'{prov}\': {e.response.text[:200]}")
            if e.response.status_code in (408, 409, 429, 500, 502, 503) and tentativa < 2:
                time.sleep(2.0 * (tentativa + 1))
                continue
            break
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
            ultimo = LLMError(f"Falha de rede com \'{prov}\': {e.__class__.__name__}")
            if tentativa < 2:
                time.sleep(2.0 * (tentativa + 1))
                continue
            break
    raise ultimo


def _anthropic(base, chave, modelo, sistema, mensagens, temperatura, max_tokens, timeout, ao_tokeno) -> str:
    corpo: dict[str, Any] = {
        "model": modelo, "max_tokens": max_tokens, "temperature": temperatura,
        "system": sistema, "messages": mensagens,
    }
    cab = {"x-api-key": chave, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    if ao_tokeno is None:
        r = httpx.post(base + "/messages", json=corpo, headers=cab, timeout=timeout)
        r.raise_for_status()
        dados = r.json()
        return "".join(b.get("text", "") for b in dados.get("content", []) if b.get("type") == "text")
    partes: list[str] = []
    with httpx.stream("POST", base + "/messages", json={**corpo, "stream": True}, headers=cab, timeout=timeout) as resp:
        resp.raise_for_status()
        for linha in resp.iter_lines():
            if not linha.startswith("data:"):
                continue
            payload = linha[5:].strip()
            if payload == "[DONE]":
                break
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "content_block_delta":
                tok = ev.get("delta", {}).get("text", "")
                if tok:
                    partes.append(tok)
                    ao_tokeno(tok)
    return "".join(partes)


def _openai_compatible(base, chave, modelo, sistema, mensagens, temperatura, max_tokens, timeout, ao_tokeno) -> str:
    msgs = [{"role": "system", "content": sistema}] + list(mensagens)
    corpo: dict[str, Any] = {
        "model": modelo, "messages": msgs,
        "temperature": temperatura, "max_tokens": max_tokens,
    }
    cab = {"Authorization": f"Bearer {chave}", "content-type": "application/json"}
    if ao_tokeno is None:
        r = httpx.post(base + "/chat/completions", json=corpo, headers=cab, timeout=timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"] or ""
    partes: list[str] = []
    with httpx.stream("POST", base + "/chat/completions", json={**corpo, "stream": True}, headers=cab, timeout=timeout) as resp:
        resp.raise_for_status()
        for linha in resp.iter_lines():
            if not linha.startswith("data:"):
                continue
            payload = linha[5:].strip()
            if payload == "[DONE]":
                break
            try:
                ev = json.loads(payload)
            except json.JSONDecodeError:
                continue
            try:
                tok = ev["choices"][0].get("delta", {}).get("content")
            except (KeyError, IndexError, TypeError):
                tok = None
            if tok:
                partes.append(tok)
                ao_tokeno(tok)
    return "".join(partes)


def chat_json(sistema: str, mensagens: list[dict[str, str]], *, cfg: dict | None = None, modelo: str | None = None, **kw: Any) -> Any:
    """chat() + extração do primeiro JSON da resposta."""
    return extrair_json(chat(sistema, mensagens, cfg=cfg, modelo=modelo, **kw))


def extrair_json(texto: str) -> Any:
    """Extrai o primeiro objeto/array JSON de um texto de LLM (com ou sem fence)."""
    texto = texto.strip()
    for padrao in (r"```json\s*(.+?)```", r"```\s*(\{.+?\})```", r"```\s*(\[.+?\])```"):
        m = re.search(padrao, texto, re.S)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(texto):
        if ch in "{[":
            try:
                valor, _ = dec.raw_decode(texto[i:])
                return valor
            except json.JSONDecodeError:
                continue
    raise LLMError(f"LLM não devolveu JSON legível. Início da resposta: {texto[:160]!r}")
