# Guia de uso

## Receitas

### 1. Paper do zero, com entrevista
```bash
papo-pepper novo "Dobradiço de proteínas com modelos de linguagem" --entrevista
```
A entrevista faz 9 perguntas (assunto → restrições). Responda devagar: cada resposta muda o plano.

### 2. De um áudio ou transcrição
```bash
papo-pepper novo "Sua tese sobre X" --audio fala-do-especialista.m4a
```
Transcreve (faster-whisper; extra `pip install 'papo-pepper[audio]'`), extrai as teses centrais
e ainda pergunta o que falta.

### 3. De um repositório (documentação + paper)
```bash
papo-pepper novo "Análise do sistema X" --repo ./meu-projeto
```
Gera `00_perfil_repositorio.json` (linguagens, AST, deps, testes, CI), roda o Documentalista
na segunda fase e produz paper técnico + documentação.

### 4. Analisar/melhorar material existente
```bash
papo-pepper analisar meu-texto.md          # relatório + correções automáticas
papo-pepper analisar ./repo                # perfil + documentação + paper
```

### 5. Exportar de novo (ou formato extra)
```bash
papo-pepper exportar papers/2026-09-22-tema            # tudo
papo-pepper exportar papers/2026-09-22-tema --formatos pdf
```

### 6. Reexecutar UMA etapa (trocar modelo, refinar à mão)
```bash
papo-pepper etapa juiz --paper papers/2026-09-22-tema --modelo gpt-5
papo-pepper estado papers/2026-09-22-tema
```

## FAQ

- **Troquei de modelo no meio do paper?** Use `etapa <rolo> --modelo <tag>`; etapas anteriores
  ficam como estão. Use `--forcar` no `novo` para repetir tudo.
- **Não tenho API key?** A pipeline gera esqueletos (cartões de agente). Complete manualmente
  ou delegue para Claude Code/Codex/OpenClaw/Hermes seguindo `skills/papo-pepper/SKILL.md` —
  depois rode `papo-pepper exportar` para as saídas finais.
- **Formatos de áudio?** m4a/mp3/wav/ogg via faster-whisper; ou passe a transcrição em .txt/.srt.
- **ABNT?** `PAPER_CITACAO=abnt` (ou responda "abnt" na entrevista); o Cientista numera conforme o estilo.
- **Meu paper tem 40 páginas?** `profundidade: maxima` no config ou "maxima" na entrevista —
  o Especialista dobra a palavra-alvo por seção e o Retador passa de 10 para 20 desafios.
- **Onde fica tudo?** `papers/<AAAA-MM-DD>-<slug>/` — o log `log/pipeline.jsonl` registra cada fase.
