# Modelos recomendados

> **Regra de ouro do Papo Pepper: use SEMPRE a versão mais recente disponível no seu provedor.**
> A lista abaixo é referência curada em **2026-09-22** — confirme a tag exata mais nova no catálogo
> do provedor antes de rodar (`pip show` de modelos não existe: olhe o console do provedor).

## Curadoria (famílias de ponta)

| Provedor | Família recomendada | Variáveis / endpoint |
| --- | --- | --- |
| Anthropic | Claude Opus 4.x (razão máxima) / Sonnet 4.x (equilíbrio) | `ANTHROPIC_API_KEY` → default `claude-sonnet-4-5` |
| OpenAI | GPT-5 (reasoning) / GPT-5-mini (volume) | `OPENAI_API_KEY` → default `gpt-5` |
| Google | Gemini 2.5 Pro / linha Gemini 3 | via OpenRouter: `google/gemini-2.5-pro` |
| DeepSeek | DeepSeek V3.x / R1 (razão) | via OpenRouter: `deepseek/deepseek-chat` |
| Meta | Llama 4 / Llama 3.3 70B | Ollama local: `llama4` / `llama3.3:70b` |
| Qwen | Qwen3-Max | via OpenRouter: `qwen/qwen3-max` |

## Estratégia por fase (opcional, para economizar token)

| Fase | Perfil ideal | Modelo mais barato aceitável |
| --- | --- | --- |
| editor, pesquisador, cientista | forte em razão e síntese | Sonnet 4.x / GPT-5-mini |
| especialista (matemática) | forte em formalização | Opus 4.x / GPT-5 |
| cetico, retador, validador | forte em crítica | Opus 4.x / GPT-5 / DeepSeek R1 |
| juiz | forte em ponderação | Opus 4.x / GPT-5 |
| diagramador, escritor, revisor | bom em prosa/forma | Sonnet 4.x / GPT-5-mini / Haiku |

Para usar modelos diferentes por fase, rode etapas avulsas:
`papo-pepper etapa juísz --paper <dir> --modelo gpt-5` (o `--modelo` vale só para aquela etapa).

## Configuração

Ordem de precedência: defaults < `~/.config/papo-pepper/config.yaml` < variáveis de ambiente.

```bash
# qualquer um destes:
export ANTHROPIC_API_KEY=sk-ant-...        # + PAPER_MODEL opcional
export OPENAI_API_KEY=sk-...               # default gpt-5
export OPENROUTER_API_KEY=sk-or-...        # catálogo único
export OLLAMA=true                          # local, sem chave

# ou override total (endpoint compatível OpenAI: vLLM, LM Studio, Groq…)
export PAPER_PROVIDER=custom
export PAPER_BASE_URL=https://seu-endpoint/v1
export PAPER_API_KEY=...
export PAPER_MODEL=seu-modelo
export PAPER_AUTOR="Seu Nome"              # aparece na capa
export PAPER_CITACAO=apa                   # apa | ieee | vancouver | abnt | livre
export PAPER_DIR=./papers                  # onde os papers nascem
```

`papo-pepper models` mostra o que está ativo agora + esta curadoria.
Curadoria editável: `papo_pepper/models.py` → `CURADOS` / `DICAS`.
