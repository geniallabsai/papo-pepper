#!/usr/bin/env bash
# 🌶️ Papo Pepper — desinstalador (Linux/macOS)
#   ./uninstall.sh             remove skills/adapters dos agentes
#   ./uninstall.sh --pacote    + remove o pacote Python e o clone-fonte
set -euo pipefail
PACOTE=0
for a in "$@"; do case "$a" in --pacote) PACOTE=1 ;; esac; done

PY="$(command -v python3 || command -v python)"
if "$PY" -c 'import papo_pepper' >/dev/null 2>&1; then
  "$PY" -m papo_pepper.installers --remover
else
  echo "pacote papo-pepper não está instalado (só removendo arquivos soltos)"
fi

if [ "$PACOTE" -eq 1 ]; then
  "$PY" -m pip uninstall -y papo-pepper >/dev/null 2>&1 || true
  rm -rf "$HOME/.local/share/papo-pepper-src"
  echo "pacote Python e clone-fonte removidos"
fi

echo "feito. Se ainda v virar blocos marcados '# >>> papo-pepper >>>' em AGENTS.md/CLAUDE.md,"
echo "apague as seções entre as marcas '#' manualmente."
