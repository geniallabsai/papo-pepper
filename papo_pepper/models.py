"""Curadoria de modelos LLM (referência 2026-09-22) + estratégia por fase.

Regra de casa: prefira SEMPRE a versão mais recente disponível no seu provedor.
As tags abaixo são pontos de partida — confirme a tag atual no catálogo do provedor.
"""
from __future__ import annotations

REFERENCIA = "2026-09-22"

CURADOS: list[tuple[str, str, str, str]] = [
    # (provedor, recomendação, como configurar, exemplo de tag)
    ("Anthropic",
     "Claude linha Opus (razão máxima) / Sonnet (equilíbrio custo-razão)",
     "export ANTHROPIC_API_KEY=...",
     "claude-opus-4-5 | claude-sonnet-4-5"),
    ("OpenAI",
     "Família GPT-5 (raciocínio longo) / GPT-5-mini (alto volume)",
     "export OPENAI_API_KEY=...",
     "gpt-5 | gpt-5-mini"),
    ("Google",
     "Gemini 2.5 Pro / linha Gemini 3 (janelas enormes, multimodal)",
     "export OPENROUTER_API_KEY=...  →  PAPER_MODEL=google/gemini-2.5-pro",
     "google/gemini-2.5-pro"),
    ("DeepSeek",
     "DeepSeek V3.x (geral) / R1 (razão) — excelente custo",
     "export OPENROUTER_API_KEY=...  →  PAPER_MODEL=deepseek/deepseek-v3",
     "deepseek/deepseek-v3"),
    ("Meta",
     "Llama 4 / Llama 3.3 70B (local via Ollama)",
     "export OLLAMA=true  (servidor local: ollama serve)",
     "llama4 | llama3.3:70b"),
    ("Qwen",
     "Qwen3-Max (multilíngue forte, bom em pt-BR)",
     "export OPENROUTER_API_KEY=...  →  PAPER_MODEL=qwen/qwen3-max",
     "qwen/qwen3-max"),
]

ESTRATEGIA_POR_FASE: list[tuple[str, str, str]] = [
    ("Editor-Chefe, Especialista, Juiz", "razão máxima", "Opus / GPT-5 (pro) / Gemini Pro"),
    ("Pesquisador, Cientista da Informação", "boa razão + janelão", "Sonnet / GPT-5 / DeepSeek V3"),
    ("Cético, Retador, Validador", "razão forte (adversarial)", "R1 / o mesmo do Juiz"),
    ("Diagramador, Escritor, Revisor", "bom e rápido", "Sonnet mini / GPT-5-mini / Qwen3"),
]

DICAS: list[str] = [
    "Sempre confira no catálogo do provedor a tag MAIS RECENTE da família antes de configurar.",
    "Um único bom modelo em todas as fases é o setup recomendado; misturar só quando houver motivo de custo.",
    "Local? Ollama + modelo 70B+ cobre a pipeline inteira: export OLLAMA=true.",
    "Para matemática/ML, prefira modelos com bom alinhamento a código (famílias acima cobrem).",
    "Override rápido: papo-pepper novo <tema> --modelo <tag> (por comando, sem tocar em config).",
]


def linhas_curados() -> list[str]:
    out = [f"CURIADOR DE MODELOS — referência {REFERENCIA}"]
    for prov, rec, cfg, ex in CURADOS:
        out.append(f"  • {prov}: {rec}\n      {cfg}\n      ex.: {ex}")
    return out


def linhas_estrategia() -> list[str]:
    return [f"  • {f}: {perfil} → {ex}" for f, perfil, ex in ESTRATEGIA_POR_FASE]
