"""Instala skills e adapters nos agentes: Codex, Claude Code, OpenClaw, Hermes (+ genérico AGENTS.md).

Idempotente: tudo entra em blocos marcados (>> papo-pepper >>) ou em diretórios próprios.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parent.parent
MARK_A = "# >>> papo-pepper >>>"
MARK_B = "# <<< papo-pepper <<<"


def detectar_agentes() -> dict[str, str | None]:
    home = Path.home()
    det: dict[str, str | None] = {
        "codex": shutil.which("codex"),
        "claude": shutil.which("claude"),
        "openclaw": shutil.which("openclaw") or (str(home / ".openclaw") if (home / ".openclaw").exists() else None),
        "hermes": shutil.which("hermes") or (str(home / ".hermes") if (home / ".hermes").exists() else None),
    }
    return det


def _blocar(destino: Path, conteudo_bloco: str) -> str:
    destino.parent.mkdir(parents=True, exist_ok=True)
    atual = destino.read_text(encoding="utf-8") if destino.exists() else ""
    bloco = f"{MARK_A}\n{conteudo_bloco.strip()}\n{MARK_B}"
    if MARK_A in atual and MARK_B in atual:
        novo = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B), lambda m: bloco, atual, flags=re.S)
        destino.write_text(novo, encoding="utf-8")
        return "atualizado"
    sufixo = ("\n\n" if atual.strip() else "") + bloco + "\n"
    destino.write_text(atual.rstrip() + sufixo, encoding="utf-8")
    return "criado" if not atual.strip() else "adicionado"


def _desmarcar(destino: Path) -> bool:
    if not destino.exists():
        return False
    atual = destino.read_text(encoding="utf-8")
    if MARK_A not in atual or MARK_B not in atual:
        return False
    novo = re.sub(re.escape(MARK_A) + r".*?" + re.escape(MARK_B) + r"\n?", "", atual, flags=re.S)
    destino.write_text(novo.strip() + "\n" if novo.strip() else "", encoding="utf-8")
    return True


def _copiar_skills(dest_skills: Path) -> int:
    raiz_skills = RAIZ_REPO / "skills"
    n = 0
    dest_skills.mkdir(parents=True, exist_ok=True)
    for sk in sorted(raiz_skills.iterdir()):
        if not sk.is_dir():
            continue
        alvo = dest_skills / sk.name
        if alvo.exists():
            shutil.rmtree(alvo)
        shutil.copytree(sk, alvo)
        n += 1
    return n


def _mcp_codex() -> None:
    cfg = Path.home() / ".codex" / "config.toml"
    _blocar(cfg, f'[mcp_servers.papo_pepper]\ncommand = "{sys.executable}"\nargs = ["-m", "papo_pepper.mcp_server"]')


def instalar(alvo: str | None = None, com_mcp: bool = False) -> dict[str, str]:
    det = detectar_agentes()
    alvos = [alvo] if alvo else [a for a in det if det[a]]
    if not alvos:
        return {"aviso": "nenhum agente detectado (codex/claude/openclaw/hermes). Use --alvo generico para escrever AGENTS.md no diretório atual."}
    plat = RAIZ_REPO / "platforms"
    resumo: dict[str, str] = {}

    for nome in alvos:
        try:
            if nome == "generico":
                destino = Path.cwd() / "AGENTS.md"
                resumo["generico"] = f"AGENTS.md {_blocar(destino, (plat / 'AGENTS.md').read_text(encoding='utf-8'))} em {destino}"
            elif nome == "codex":
                destino = Path.home() / ".codex" / "AGENTS.md"
                resumo["codex"] = f"{destino} ({_blocar(destino, (plat / 'codex' / 'AGENTS.md').read_text(encoding='utf-8'))})"
                if com_mcp:
                    _mcp_codex()
                    resumo["codex-mcp"] = "~/.codex/config.toml ([mcp_servers.papo_pepper])"
            elif nome == "claude":
                ag_dir = Path.home() / ".claude" / "agents"
                ag_dir.mkdir(parents=True, exist_ok=True)
                src_agents = plat / "claude" / "agents"
                n_agents = 0
                for f in sorted(src_agents.glob("*.md")):
                    shutil.copy2(f, ag_dir / f.name)
                    n_agents += 1
                sk_dest = Path.home() / ".claude" / "skills" / "papo-pepper"
                if sk_dest.exists():
                    shutil.rmtree(sk_dest)
                shutil.copytree(RAIZ_REPO / "skills" / "papo-pepper", sk_dest)
                claude_md = Path.home() / ".claude" / "CLAUDE.md"
                _blocar(claude_md, (plat / "claude" / "CLAUDE.md").read_text(encoding="utf-8"))
                resumo["claude"] = f"{n_agents} subagentes em {ag_dir} + skill em {sk_dest} + CLAUDE.md"
                if com_mcp and det.get("claude"):
                    r = subprocess.run(["claude", "mcp", "add", "--scope", "user", "papo-pepper", "--",
                                        sys.executable, "-m", "papo_pepper.mcp_server"],
                                       capture_output=True, text=True, timeout=60)
                    resumo["claude-mcp"] = ("registrado (claude mcp add)" if r.returncode == 0
                                             else "manual: " + (r.stdout + r.stderr).strip()[:140])
                else:
                    resumo["claude-mcp"] = "snippet: docs/MCP.md (seção Claude)" if com_mcp else "—"
            elif nome == "openclaw":
                ws = Path.home() / ".openclaw" / "workspace"
                n = _copiar_skills(ws / "skills")
                agentes = ws / "AGENTS.md"
                resumo["openclaw"] = f"{ws} ({n} skills + AGENTS.md {_blocar(agentes, (plat / 'openclaw' / 'AGENTS.md').read_text(encoding='utf-8'))})"
            elif nome == "hermes":
                pasta = Path.home() / ".hermes" / "agents" / "papo-pepper"
                pasta.mkdir(parents=True, exist_ok=True)
                shutil.copy2(plat / "hermes" / "AGENT.md", pasta / "AGENT.md")
                n = _copiar_skills(pasta / "skills")
                resumo["hermes"] = f"{pasta} (AGENT.md + {n} skills)"
            else:
                resumo[nome] = "desconhecido"
        except Exception as e:  # noqa: BLE001
            resumo[nome] = f"erro: {e.__class__.__name__}: {e}"
    return resumo


def remover() -> dict[str, str]:
    home = Path.home()
    resumo: dict[str, str] = {}
    alvos = []
    for nome, caminho in (("codex", home / ".codex" / "AGENTS.md"),
                          ("claude", home / ".claude" / "CLAUDE.md"),
                          ("openclaw", home / ".openclaw" / "workspace" / "AGENTS.md")):
        if _desmarcar(caminho):
            resumo[nome] = "bloco removido de " + str(caminho)
            alvos.append(nome)
    if _desmarcar(home / ".codex" / "config.toml"):
        resumo["codex-mcp"] = "mcp_servers.papo_pepper removido do config.toml"
    for alvo in (home / ".claude" / "agents", ):
        if alvo.is_dir():
            for f in alvo.glob("pp-*.md"):
                f.unlink()
                resumo.setdefault("claude", "")
    resumo["claude"] = resumo.get("claude", "") and "subagentes pp-* removidos"
    sk = home / ".claude" / "skills" / "papo-pepper"
    if sk.exists():
        shutil.rmtree(sk)
        resumo["claude-skill"] = "removida"
    ws = home / ".openclaw" / "workspace" / "skills"
    if ws.is_dir():
        for d in list(ws.iterdir()):
            if d.name == "papo-pepper" or d.name.startswith("pp-"):
                shutil.rmtree(d)
        resumo["openclaw-skills"] = "removidas"
    hm = home / ".hermes" / "agents" / "papo-pepper"
    if hm.exists():
        shutil.rmtree(hm)
        resumo["hermes"] = "agente removido"
    ag = Path.cwd() / "AGENTS.md"
    if _desmarcar(ag):
        resumo["generico"] = f"bloco removido de {ag}"
    return resumo or {"aviso": "nada para remover"}


def principal() -> None:
    ap = argparse.ArgumentParser(description="Instalador de skills/adapters do Papo Pepper.")
    ap.add_argument("--alvo", default=None, help="codex | claude | openclaw | hermes | generico")
    ap.add_argument("--mcp", action="store_true", help="registra o servidor MCP onde suportado")
    ap.add_argument("--remover", action="store_true", help="remove os adapters instalados")
    args = ap.parse_args()
    dados = remover() if args.remover else instalar(alvo=args.alvo, com_mcp=args.mcp)
    for k, v in dados.items():
        print(f"  • {k}: {v}")
    if not args.remover:
        print("\nDica: prefira sempre os modelos MAIS RECENTES do seu provedor (papo-pepper models).")


if __name__ == "__main__":
    principal()
