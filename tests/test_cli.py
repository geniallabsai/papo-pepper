import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _env_limpo():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(("ANTHROPIC", "OPENAI", "OPENROUTER", "OLLAMA", "PAPER_", "S2_"))}


def test_cli_help_mostra_todos_os_comandos():
    r = subprocess.run([sys.executable, "-m", "papo_pepper", "--help"],
                       capture_output=True, text=True, cwd=RAIZ, env=_env_limpo())
    assert r.returncode == 0, r.stderr
    for cmd in ("novo", "analisar", "exportar", "estado", "etapa", "models", "setup", "config"):
        assert cmd in r.stdout, f"faltando comando {cmd!r} no help"


def test_cli_models_sem_provedor_mostra_curadoria():
    r = subprocess.run([sys.executable, "-m", "papo_pepper", "models"],
                       capture_output=True, text=True, cwd=RAIZ, env=_env_limpo())
    assert r.returncode == 0, r.stderr
    assert "CURADORIA DE MODELOS" in r.stdout
