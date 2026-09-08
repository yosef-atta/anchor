import json
from pathlib import Path

import typer
from rich.console import Console

from anchor import __version__
from anchor.core import add_decision, add_note, get_project_status, initialize_project
from anchor.models import DecisionInput, NoteInput, Origin

app = typer.Typer(
    name="anchor",
    help="Anchor: Local project-memory and decision system for agentic software development.",
    no_args_is_help=True,
)

add_app = typer.Typer(
    name="add",
    help="Add persistent project memory records (decisions, notes).",
    no_args_is_help=True,
)
app.add_typer(add_app, name="add")

console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"anchor version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show Anchor version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Anchor CLI."""


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
        console.print("  • SQLite database: [cyan].anchor/anchor.db[/cyan]")
        console.print("  • Agent rules: [cyan]AGENTS.md[/cyan], [cyan]CLAUDE.md[/cyan]")
        if is_existing:
            console.print("  • Project type: [yellow]existing[/yellow] (bootstrap status: [yellow]pending[/yellow])")
        else:
            console.print("  • Project type: [green]new[/green]")
            
        console.print("\n[bold]MCP Server Configuration:[/bold]")
        console.print(mcp_json_str)
    except Exception as e:
        console.print(f"[bold red]Error initializing project:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


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
        raise typer.Exit(code=1) from e


@add_app.command(name="decision")
def add_decision_cmd(
    title: str = typer.Option(..., "--title", help="Short title describing the decision."),
    category: str = typer.Option(..., "--category", help="Category classification."),
    decision: str = typer.Option(..., "--decision", help="The decision that was made."),
    reason: str = typer.Option(..., "--reason", help="The rationale behind the decision."),
    origin: Origin = typer.Option(Origin.LIVE, "--origin", help="Origin: live or bootstrap."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
):
    """Add a new decision to project memory."""
    try:
        input_data = DecisionInput(
            title=title,
            category=category,
            decision=decision,
            reason=reason,
            origin=origin,
        )
        record = add_decision(input_data, project_path=path)
        console.print(f"[bold green]✓[/bold green] Added decision [bold cyan]{record.id}[/bold cyan]: {record.title}")
        console.print(f"  • Category: {record.category}")
        console.print(f"  • Decision: {record.decision}")
        console.print(f"  • Reason: {record.reason}")
        console.print(f"  • Origin: {record.origin.value}")
    except Exception as e:
        console.print(f"[bold red]Error adding decision:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


@add_app.command(name="note")
def add_note_cmd(
    title: str = typer.Option(..., "--title", help="Short title describing the note."),
    category: str = typer.Option(..., "--category", help="Category classification."),
    text: str = typer.Option(..., "--text", help="Note text content."),
    origin: Origin = typer.Option(Origin.LIVE, "--origin", help="Origin: live or bootstrap."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
):
    """Add a new note to project memory."""
    try:
        input_data = NoteInput(
            title=title,
            category=category,
            text=text,
            origin=origin,
        )
        record = add_note(input_data, project_path=path)
        console.print(f"[bold green]✓[/bold green] Added note [bold cyan]{record.id}[/bold cyan]: {record.title}")
        console.print(f"  • Category: {record.category}")
        console.print(f"  • Text: {record.text}")
        console.print(f"  • Origin: {record.origin.value}")
    except Exception as e:
        console.print(f"[bold red]Error adding note:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()
