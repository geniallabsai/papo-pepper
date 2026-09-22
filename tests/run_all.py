#!/usr/bin/env python3
"""Runner simples: descobre test_*.py em tests/ e roda cada função test_*."""
from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

RAIZ_TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ_TESTS))
sys.path.insert(0, str(RAIZ_TESTS.parent))

falhas = 0
totais = 0
for modulo_arq in sorted(RAIZ_TESTS.glob("test_*.py")):
    nome_mod = modulo_arq.stem
    try:
        mod = importlib.import_module(nome_mod)
    except Exception:
        falhas += 1
        totais += 1
        print(f"FAIL {nome_mod}: nao deu nem para importar o modulo")
        traceback.print_exc()
        continue
    for fn in sorted(n for n in dir(mod) if n.startswith("test_")):
        totais += 1
        try:
            getattr(mod, fn)()
            print(f"PASS {nome_mod}.{fn}")
        except Exception:
            falhas += 1
            print(f"FAIL {nome_mod}.{fn}")
            traceback.print_exc()

print()
if falhas == 0:
    print(f"TODOS OS TESTES PASSARAM ✔ ({totais} verificacoes)")
else:
    print(f"{falhas}/{totais} FALHARAM ✘")
sys.exit(1 if falhas else 0)
