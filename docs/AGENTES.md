# A equipe — 12 papéis

Cada papel tem: cartão em `skills/pp-*/SKILL.md`, prompt em `papo_pepper/prompts/*.md`,
artefato com dono único na pipeline, e subagente pronto no Claude Code.

| Papel (pipeline) | Skill | Artefato | Pergunta que responde | Falha quando… |
| --- | --- | --- | --- | --- |
| editor (Editor-Chefe) | pp-editor | 01_plano.md | O que escrevo, para quem, em que ordem? | Seção genérica; sem pergunta de pesquisa |
| pesquisador (Pesquisador Profundo) | pp-researcher | 02_fontes.json + notas | O que a evidência primária diz? | Fonte ≤ conf. 2 carregando conclusão |
| cientista (Cientista da Informação) | pp-info-scientist | 03_mapa_informacional.md | Como a evidência se organiza? | Numeração de refs inconsistente |
| especialista (Especialista de Domínio) | pp-mathlab | 04_secoes/*.md | O conteúdo técnico sustenta-se? | Afirmação factual sem [n] |
| cetico (Cético) | pp-skeptic | 05_relatorio_cetico.md | Onde o texto racha? | Ataque sem citar trecho exato |
| retador (Retador Adversarial) | pp-challenger | 06_desafios.md | O que um revisor hostil perguntaria? | Desafio sem teste objetivo |
| validador (Validador) | pp-validator | 07_validacao.md | Reproduz? Os números batem? | Verificação sem mostrar a conta |
| juiz (Juiz Revisor) | pp-judge | 08_veredito.md (+json) | Aceito ou mando revisar? | REVISAR sem alteração obrigatória concreta |
| diagramador (Diagramador) | pp-diagrammer | 09_figuras.md + figuras/ | Qual figura responde qual pergunta? | > 12 nós ou rótulo > 6 palavras |
| escritor (Escritor Integrador) | pp-writer | 10_manuscrito_final.md | O paper inteiro coesa? | Resposta a desafio fora do corpo do texto |
| revisor (Revisor Final) | pp-polisher | 11_revisao.md | Forma impecável? | Mudança de argumento (isso é proibido) |
| documentalista (Documentalista de Código) | pp-repo-paper | 04_documento_codigo.md | O que este repositório faz e como? | Fluxo principal sem caminho arquivo:função |

**Ordem inegociável:** editor → [documentalista se repositório] → pesquisador → cientista →
especialista → **cetico → retador → validador** → juiz → diagramador → escritor → revisor.

**Papel extra (não-pipeline):** `pp-interviewer` conduz a entrevista de intake (mínimo 5 perguntas:
assunto, público, tipo, objetivo, dados, objeções, tom, citação, restrições).
