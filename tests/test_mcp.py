import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _troca(proc, msg):
    proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def test_mcp_initialize_list_and_tools():
    proc = subprocess.Popen([sys.executable, "-m", "papo_pepper.mcp_server"],
                            cwd=RAIZ, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        r = _troca(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-06-18"}})
        assert r["result"]["serverInfo"]["name"] == "papo-pepper"

        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        r = _troca(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        nomes = {t["name"] for t in r["result"]["tools"]}
        assert {"pp_buscar_web", "pp_ler_pagina", "pp_arxiv", "pp_eval_python",
                "pp_stats", "pp_ast_python", "pp_arvore", "pp_dependencias",
                "pp_docx", "pp_pdf"} <= nomes

        r = _troca(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                          "params": {"name": "pp_stats", "arguments": {"amostra": [1, 2, 3, 4]}}})
        assert "media: 2.5" in r["result"]["content"][0]["text"]

        r = _troca(proc, {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                          "params": {"name": "pp_eval_python", "arguments": {"code": "print(6*7)"}}})
        assert "42" in r["result"]["content"][0]["text"]

        r = _troca(proc, {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                          "params": {"name": "pp_arvore", "arguments": {"caminho": "."}}})
        assert "papo_pepper" in r["result"]["content"][0]["text"]
    finally:
        proc.terminate()
        proc.wait(timeout=10)
