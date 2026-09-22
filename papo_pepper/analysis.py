"""Análise de material existente (texto) e de repositórios de código."""
from __future__ import annotations

import ast
import json
import re
from collections import Counter
from pathlib import Path

EXT_LINGUAGEM = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx",
    ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cs": "csharp", ".swift": "swift",
    ".kt": "kotlin", ".sh": "bash", ".html": "html", ".css": "css",
}
DIRS_IGNORE = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
               ".next", "target", ".idea", ".vscode", "coverage", ".tox", ".mypy_cache", "vendor"}


def detectar_tipo(caminho: Path) -> str | None:
    """'repo' | 'texto' | None."""
    caminho = Path(caminho)
    if caminho.is_dir():
        if ((caminho / ".git").exists() or (caminho / "pyproject.toml").exists()
                or (caminho / "package.json").exists() or (caminho / "go.mod").exists()):
            return "repo"
        if any(caminho.glob("*.py")) or any(caminho.glob("*.js")) or any(caminho.glob("*.go")):
            return "repo"
        return None
    if caminho.suffix.lower() in {".md", ".markdown", ".txt", ".rst", ".docx", ".html"}:
        return "texto"
    return None


def ler_documento(caminho: Path) -> str:
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".docx":
        from docx import Document
        d = Document(str(caminho))
        return "\n\n".join(p.text for p in d.paragraphs)
    return caminho.read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ repositórios
def _linhas(arq: Path) -> int:
    try:
        return arq.read_text(encoding="utf-8", errors="replace").count("\n") + 1
    except OSError:
        return 0


def _deps_manifesto(nome: str, conteudo: str) -> list[str]:
    deps: list[str] = []
    if nome in ("pyproject.toml", "setup.py"):
        m = re.search(r"(?:dependencies|install_requires)\s*=\s*\[(.*?)\]", conteudo, re.S)
        if m:
            deps = re.findall(r"[\"']([^\"'\n]+)[\"']", m.group(1))
    elif nome == "requirements.txt":
        deps = [l.split("#")[0].strip() for l in conteudo.splitlines() if l.strip() and not l.startswith("-")]
    elif nome == "package.json":
        try:
            dados = json.loads(conteudo)
            deps = list(dados.get("dependencies", {})) + list(dados.get("devDependencies", {}))
        except json.JSONDecodeError:
            pass
    elif nome == "go.mod":
        deps = re.findall(r"^\s+([\w./-]+)\s+v[\w.+-]+", conteudo, flags=re.M)
    elif nome == "Cargo.toml":
        sec = re.search(r"\[dependencies\]\n(.*?)(\n\[|$)", conteudo, re.S)
        if sec:
            deps = [l.split("=")[0].strip() for l in sec.group(1).splitlines() if "=" in l]
    return sorted(set(deps))


def _ast_python(arquivos: list[Path]) -> dict:
    funs = cls = docf = docc = 0
    tot_linhas = 0
    n_modulos = 0
    for p in arquivos:
        n_modulos += 1
        tot_linhas += _linhas(p)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funs += 1
                if ast.get_docstring(node):
                    docf += 1
            elif isinstance(node, ast.ClassDef):
                cls += 1
                if ast.get_docstring(node):
                    docc += 1
    return {
        "modulos_python": n_modulos,
        "linhas_python": tot_linhas,
        "funcoes": funs,
        "classes": cls,
        "funcoes_com_docstring": docf,
        "classes_com_docstring": docc,
        "cobertura_docstring_pct": round(100 * docf / max(funs, 1), 1),
    }


def _arvore(repo: Path, maximo: int = 120) -> str:
    linhas: list[str] = []
    cont = 0

    def walk(p: Path, prof: int) -> None:
        nonlocal cont
        try:
            filhos = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except OSError:
            return
        for child in filhos:
            if cont >= maximo:
                linhas.append("  " * prof + "… (truncado)")
                return
            if child.name in DIRS_IGNORE or child.name.startswith("."):
                continue
            linhas.append("  " * prof + (child.name + "/" if child.is_dir() else child.name))
            cont += 1
            if child.is_dir():
                walk(child, prof + 1)

    walk(repo, 0)
    return "\n".join(linhas[:maximo])


def _licenca(repo: Path) -> str:
    for cand in repo.glob("LICENSE*"):
        try:
            return cand.read_text(errors="replace").splitlines()[0][:120]
        except OSError:
            continue
    for cand in repo.glob("LICEN[CS]*E"):
        try:
            return cand.read_text(errors="replace").splitlines()[0][:120]
        except OSError:
            continue
    return "(nenhuma licença encontrada)"


def analisar_repositorio(repo: Path) -> dict:
    repo = Path(repo).resolve()
    arquivos: list[Path] = []
    linguagens: Counter = Counter()
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        if any(part in DIRS_IGNORE for part in p.parts):
            continue
        sufixo = p.suffix.lower()
        if sufixo in EXT_LINGUAGEM:
            linguagens[EXT_LINGUAGEM[sufixo]] += 1
            arquivos.append(p)
        if len(arquivos) >= 1500:
            break
    manifests: dict[str, list[str]] = {}
    for nome in ("pyproject.toml", "setup.py", "requirements.txt", "package.json",
                 "go.mod", "Cargo.toml", "pom.xml", "Gemfile"):
        arq = repo / nome
        if arq.exists():
            try:
                deps = _deps_manifesto(nome, arq.read_text(errors="replace")[:20000])
            except Exception:  # noqa: BLE001
                deps = []
            if deps or nome in ("pyproject.toml", "package.json"):
                manifests[nome] = deps
    readme = next((repo / n for n in ("README.md", "README.rst", "README.txt", "Readme.md")
                   if (repo / n).exists()), None)
    testes = sum(1 for p in arquivos if re.search(r"(^|[_/.])test[_-]|_test\.|\.test\.|spec\.", p.name))
    ci = [str(p.relative_to(repo)) for p in repo.iterdir()
          if p.name in (".gitlab-ci.yml", "Jenkinsfile")]
    workflows = repo / ".github" / "workflows"
    if workflows.is_dir():
        ci += [str(w.relative_to(repo)) for w in sorted(workflows.iterdir())][:5]
    py_files = [a for a in arquivos if a.suffix == ".py"]
    perfil = {
        "nome": repo.name,
        "caminho": str(repo),
        "linguagens": dict(linguagens.most_common()),
        "arquivos_fonte": len(arquivos),
        "linhas_estimadas": sum(_linhas(a) for a in arquivos[:800]),
        "manifests": manifests,
        "readme": (readme.read_text(errors="replace")[:1800] if readme else ""),
        "testes_arquivos": testes,
        "ci": ci[:6],
        "licenca": _licenca(repo),
        "ast_python": _ast_python(py_files[:400]),
        "arvore_resumo": _arvore(repo),
    }
    return perfil


def perfil_para_markdown(perfil: dict) -> str:
    linhas = [
        f"# Perfil do repositório — {perfil['nome']}",
        "",
        f"- **Linguagens:** {', '.join(f'{k} ({v})' for k, v in perfil['linguagens'].items())}",
        f"- **Arquivos de fonte:** {perfil['arquivos_fonte']} · **Linhas estimadas:** {perfil['linhas_estimadas']}",
        f"- **Licença:** {perfil['licenca']}",
        f"- **Testes (arquivos):** {perfil['testes_arquivos']} · **CI:** {', '.join(perfil['ci']) or 'não detectado'}",
        "",
        "## Dependências",
        "",
    ]
    for nome, deps in perfil["manifests"].items():
        if deps:
            linhas.append(f"**{nome}:** " + ", ".join(deps[:40]))
            linhas.append("")
    astp = perfil.get("ast_python") or {}
    if astp.get("modulos_python"):
        linhas += [
            "## Saúde do código Python (AST)",
            "",
            f"- Módulos: {astp['modulos_python']} · Funções: {astp['funcoes']} · Classes: {astp['classes']}",
            f"- Docstrings: {astp['funcoes_com_docstring']}/{astp['funcoes']} funções "
            f"({astp['cobertura_docstring_pct']}%) · classes documentadas: {astp['classes_com_docstring']}/{astp['classes']}",
            "",
        ]
    if perfil.get("readme"):
        linhas += ["## README (trecho)", "", "> " + perfil["readme"].replace("\n", "\n> ")[:1200], ""]
    linhas += ["## Árvore (resumo)", "", "```", perfil["arvore_resumo"], "```"]
    return "\n".join(linhas)


# ------------------------------------------------------------------ texto
_PREENCHIMENTO = ("é importante notar", "é importante ressaltar", "como vimos anteriormente", "em suma",
                  "basicamente", "na verdade", "literalmente", "cada vez mais", "vale destacar")


def relatorio_texto(texto: str, cfg: dict | None = None) -> str:
    cfg = cfg or {}
    palavras = len(re.findall(r"\b[\w']+\b", texto, flags=re.U))
    sentencas = max(len(re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", texto))), 1)
    media_sentenca = palavras / sentencas
    titulos = re.findall(r"^(#{1,6})\s+", texto, flags=re.M)
    niveis = Counter(len(t) for t in titulos)
    citacoes = len(re.findall(r"\[\d{1,3}\]|\(\s*[A-Z][a-zA-Z]+\s*,\s*\d{4}[a-z]?\s*\)|et al\.", texto))
    enchimentos = sum(texto.lower().count(p) for p in _PREENCHIMENTO)
    tem = lambda *chaves: any(c.lower() in texto.lower() for c in chaves)  # noqa: E731
    secoes_presentes = {
        "abstract/resumo": tem("resumo", "abstract", "sumário executivo"),
        "introdução/contexto": tem("introdução", "contexto", "apresentação", "introduction"),
        "método/abordagem": tem("método", "metodologia", "abordagem", "arquitetura", "implementação"),
        "resultados/análise": tem("resultados", "análise", "benchmarks", "encontramos"),
        "discussão/limitações": tem("discussão", "limitações", "limitacao"),
        "conclusão": tem("conclusão", "considerações finais", "conclusion"),
        "referências": tem("referências", "referencias", "bibliografia", "fontes"),
    }
    qtd_secoes = sum(secoes_presentes.values())
    salto_nivel = False
    nivel_anterior = 0
    for t in titulos:
        if len(t) > nivel_anterior + 1 and nivel_anterior:
            salto_nivel = True
        nivel_anterior = len(t)
    score_estrut = min(5, 1 + qtd_secoes // 2)
    cit_por_100 = citacoes / max(palavras / 100, 1)
    score_evid = min(5, int(cit_por_100 * 4) + (1 if citacoes > 0 else 0))
    score_clar = 5 - min(3, int(enchimentos / 4)) - (1 if media_sentenca > 32 else 0)
    alvo_palavras = 6000 if (cfg.get("profundidade") == "maxima") else 2500
    score_comp = min(5, max(1, int(palavras / alvo_palavras * 5)))
    score_fmt = 5 - (1 if salto_nivel else 0) - (1 if not titulos else 0)
    fortes: list[str] = []
    fracos: list[str] = []
    if qtd_secoes >= 5:
        fortes.append(f"Estrutura com {qtd_secoes}/7 blocos canônicos presentes.")
    else:
        faltantes = [k for k, v in secoes_presentes.items() if not v]
        fracos.append("Faltando blocos canônicos: " + ", ".join(faltantes) + ".")
    if cit_por_100 >= 1.5:
        fortes.append(f"Densidade de citação saudável ({cit_por_100:.1f} por 100 palavras).")
    elif citacoes == 0:
        fracos.append("Nenhuma citação detectada — afirmações sem suporte.")
    else:
        fracos.append(f"Citações escassas ({cit_por_100:.1f}/100 palavras).")
    if media_sentenca <= 28:
        fortes.append(f"Frases curtas e diretas (média {media_sentenca:.0f} palavras).")
    else:
        fracos.append(f"Frases longas demais (média {media_sentenca:.0f} palavras).")
    if enchimentos:
        fracos.append(f"{enchimentos} expressões de preenchimento detectadas.")
    else:
        fortes.append("Sem expressão de preenchimento óbvia.")
    if palavras < alvo_palavras:
        fracos.append(f"Tamanho {palavras} palavras < alvo ~{alvo_palavras} para a profundidade pedida.")
    else:
        fortes.append(f"Volume adequado ({palavras} palavras).")
    plano = [
        "1. Criar/reorganizar seções: introdução → estado da arte → abordagem → evidência → discussão/limites → conclusão.",
        "2. Para cada afirmação factual: anexar fonte [n], dado, ou marcar explicitamente como hipótese.",
        "3. Recalcular/verificar todos os números (Validador) e declarar limitações honestas.",
        "4. Substituir conclusões afirmativas sem evidência por proposições testáveis.",
        "5. Exportar final via `papo-pepper exportar` (PDF/Word/BibTeX).",
    ]
    tab_secoes = "| bloco | presente |\n| --- | --- |\n" + "".join(
        f"| {k} | {'✅' if v else '❌'} |\n" for k, v in secoes_presentes.items())
    out = [
        "# Relatório de análise do material",
        "",
        "## Métricas",
        "",
        "| indicador | valor |",
        "| --- | --- |",
        f"| palavras | {palavras} |",
        f"| sentenças (média de palavras) | {sentencas} ({media_sentenca:.1f}) |",
        f"| títulos por nível | {dict(sorted(niveis.items()))} |",
        f"| citações detectadas | {citacoes} ({cit_por_100:.1f}/100 pal.) |",
        f"| tabelas | {len(re.findall(r'^\|', texto, flags=re.M))} linhas |",
        f"| figuras referenciadas | {len(re.findall(r'!\[', texto))} |",
        f"| enchimentos | {enchimentos} |",
        "",
        "## Estrutura canônica",
        "",
        tab_secoes,
        "## Pontuação heurística (1-5)",
        "",
        "| dimensão | nota |",
        "| --- | --- |",
        f"| estrutura | {score_estrut} |",
        f"| evidência | {score_evid} |",
        f"| clareza | {score_clar} |",
        f"| completude | {score_comp} |",
        f"| formatação | {score_fmt} |",
        "",
        "## Pontos fortes",
        "",
    ] + [f"- {f}" for f in fortes] + [""] + ["## Pontos fracos", ""] + [
        f"- {f}" for f in fracos] + ["", "## Plano de melhoria", ""] + plano
    return "\n".join(out)


def corrigir_auto(texto: str) -> tuple[str, list[str]]:
    correcoes: list[str] = []
    n = len(re.findall(r"[a-zà-ú]\S+  +\S+", texto))
    if n:
        texto = re.sub(r"(\S+)  +(?=\S)", r"\1 ", texto)
        correcoes.append(f"{n} espaços duplicados normalizados")
    n = len(re.findall(r"\s+[,.;:!?]", texto))
    if n:
        texto = re.sub(r"\s+([,.;:!?])", r"\1", texto)
        correcoes.append(f"{n} espaços antes de pontuação removidos")
    n = 0
    def _rep(m):
        nonlocal n
        n += 1
        return m.group(1)
    texto = re.sub(r"\b(\S+)(?:\s+\1)+\b", _rep, texto, flags=re.I)
    if n:
        correcoes.append(f"{n} palavras repetidas consecutivamente unificadas")
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = re.sub(r"[ \t]+$", "", texto, flags=re.M)
    return texto, correcoes
