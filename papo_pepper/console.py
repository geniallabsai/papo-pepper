"""Pequenos helpers de console (rich)."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

consola = Console()


def banner() -> None:
    consola.print(Panel.fit(
        "[bold]🌶️ PAPO PEPPER[/]\n"
        "Qualquer assunto vira um paper profundo — escrito por uma equipe multi-agente "
        "(12 papéis: pesquisa, informação, ceticismo, julgamento, diagramação, exportação).",
        border_style="red3",
    ))


def passo(msg: str) -> None:
    consola.print(f"\n[dim]────────────────────[/dim] [bold]{msg}[/bold]")


def ok(msg: str) -> None:
    consola.print(f"[green]✔ {msg}[/green]")


def aviso(msg: str) -> None:
    consola.print(f"[yellow]⚠ {msg}[/yellow]")


def erro(msg: str) -> None:
    consola.print(f"[red]✘ {msg}[/red]")
