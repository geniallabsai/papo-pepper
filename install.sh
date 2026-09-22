#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
#  🌶️ Papo Pepper — instalador (Linux/macOS) · idempotente
#
#    ./install.sh                      pacote + agentes detectados
#    ./install.sh --completo           + extras pdf/audio/math
#    ./install.sh --mcp                registra o servidor MCP (codex/claude)
#    ./install.sh --alvo claude        força um alvo específico
#    ./install.sh --somente-agentes    só skills/adapters (sem pip)
#
#  Uma linha:
#    git clone https://github.com/geniallabsai/papo-pepper.git \
#      && (cd papo-pepper && ./install.sh --completo --mcp)
# ════════════════════════════════════════════════════════════════════
set -euo pipefail

COMPLETO=0; MCP=0; SOMENTE=0; ALVO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --completo) COMPLETO=1 ;;
    --mcp) MCP=1 ;;
    --somente-agentes|--agentes) SOMENTE=1 ;;
    --alvo) ALVO="${2:-}"; shift ;;
    -h|--help) awk '/^#/{c++} c==14{exit} c>=2{sub(/^# ?/,""); print}' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1 (use --help)"; exit 1 ;;
  esac
  shift
done

echo "🌶️ Papo Pepper — instalando…"

# ---------- Python 3.10+
PY="$(command -v python3 || command -v python)" || { echo "✘ preciso de Python (python3)"; exit 1; }
"$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' \
  || { echo "✘ Python 3.10+ necessário (atual: $("$PY" --version 2>&1))"; exit 1; }
echo "  python: $("$PY" --version 2>&1) ($("$PY" -c 'import sys; print(sys.executable)'))"

# ---------- repositório (usa o atual ou clona em ~/.local/share)
RAIZ="$(pwd)"
if [ ! -f "$RAIZ/pyproject.toml" ]; then
  DEST="$HOME/.local/share/papo-pepper-src"
  if [ -d "$DEST/papo-pepper" ]; then
    RAIZ="$DEST/papo-pepper"
  elif command -v git >/dev/null 2>&1; then
    git clone --depth 1 https://github.com/geniallabsai/papo-pepper.git "$DEST/papo-pepper"
    RAIZ="$DEST/papo-pepper"
  else
    echo "✘ fora do repositório e sem git no PATH: entre na pasta do papo-pepper e rode de novo"; exit 1
  fi
fi
echo "  repositório: $RAIZ"

# ---------- pacote Python
if [ "$SOMENTE" -eq 0 ]; then
  if [ "$COMPLETO" -eq 1 ]; then
    "$PY" -m pip install --quiet -e "$RAIZ[pdf,audio,math]"
  else
    "$PY" -m pip install --quiet -e "$RAIZ"
  fi
  echo "  pacote: instalado (modo editável)"
fi
command -v papo-pepper >/dev/null 2>&1 && CLI="papo-pepper" || CLI="$PY -m papo_pepper"

# ---------- skills/adapters/MCP
cd "$RAIZ"
if [ -n "$ALVO" ] && [ "$MCP" -eq 1 ]; then $CLI setup --alvo "$ALVO" --mcp
elif [ -n "$ALVO" ]; then                    $CLI setup --alvo "$ALVO"
elif [ "$MCP" -eq 1 ]; then                  $CLI setup --mcp
else                                         $CLI setup
fi

echo
echo "✔ pronto. Próximos passos:"
echo "  • $CLI models            # ver provedor/modelos recomendados"
echo "  • $CLI novo \"seu assunto\" --entrevista"
echo "  • $CLI config autor \"Seu Nome\"   # opcional, aparece na capa"
