"""Command-line interface for Anchor."""

import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from anchor import __version__
from anchor.core import get_project_status, initialize_project

app = typer.Typer(
    name="anchor",
    help="Anchor: Local project-memory and decision system for agentic software development.",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"anchor version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show Anchor version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Anchor CLI."""
    pass


@app.command(name="init")
def init_cmd(
    path: Path = typer.Argument(
        default=Path("."),
        help="Path to project directory (defaults to current directory).",
        show_default=False,
    ),
):
    """Initialize Anchor in a project repository."""
    try:
        result = initialize_project(path)
        project_path = result["project_path"]
        is_existing = result["is_existing"]
        mcp_config = result["mcp_config"]
        
        mcp_json_str = json.dumps(mcp_config, indent=2)
        
        console.print(f"[bold green]✓[/bold green] Initialized Anchor in [bold]{project_path}[/bold]")
        console.print(f"  • SQLite database: [cyan].anchor/anchor.db[/cyan]")
        console.print(f"  • Agent rules: [cyan]AGENTS.md[/cyan], [cyan]CLAUDE.md[/cyan]")
        if is_existing:
            console.print("  • Project type: [yellow]existing[/yellow] (bootstrap status: [yellow]pending[/yellow])")
        else:
            console.print("  • Project type: [green]new[/green]")
            
        console.print("\n[bold]MCP Server Configuration:[/bold]")
        console.print(mcp_json_str)
    except Exception as e:
        console.print(f"[bold red]Error initializing project:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1)


@app.command(name="status")
def status_cmd(
    path: Path = typer.Argument(
        default=Path("."),
        help="Path to project directory (defaults to current directory).",
        show_default=False,
    ),
):
    """Show current Anchor project status."""
    try:
        status = get_project_status(path)
        if not status["initialized"]:
            console.print(f"project: {status['project']}", soft_wrap=True)
            console.print("initialized: false", soft_wrap=True)
            return
            
        console.print(f"project: {status['project']}", soft_wrap=True)
        console.print("initialized: true", soft_wrap=True)
        console.print(f"project_type: {status['project_type']}", soft_wrap=True)
        console.print(f"bootstrap_status: {status['bootstrap_status']}", soft_wrap=True)
        console.print(f"decisions: {status['decisions']}", soft_wrap=True)
        console.print(f"notes: {status['notes']}", soft_wrap=True)
    except Exception as e:
        console.print(f"[bold red]Error getting project status:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
