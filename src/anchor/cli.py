import json
from pathlib import Path

import typer
from rich.console import Console

from anchor import __version__
from anchor.core import (
    add_decision,
    add_note,
    apply_batch,
    delete_record,
    edit_record,
    get_context,
    get_project_status,
    get_record,
    initialize_project,
    search_records,
)
from anchor.models import DecisionInput, DecisionRecord, NoteInput, NoteRecord, Origin

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


@app.command(name="get")
def get_cmd(
    record_id: str = typer.Argument(..., help="ID of the record to retrieve (e.g. D-000001 or N-000001)."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
):
    """Retrieve a project memory record by ID."""
    try:
        record = get_record(record_id, project_path=path)
        if record is None:
            console.print(f"[bold red]Error:[/bold red] Record '{record_id}' not found.", highlight=False)
            raise typer.Exit(code=1)

        if isinstance(record, DecisionRecord):
            console.print(f"[bold cyan]{record.id}[/bold cyan] [bold]{record.title}[/bold] [dim]({record.category})[/dim]")
            console.print(f"  • Decision: {record.decision}")
            console.print(f"  • Reason: {record.reason}")
            console.print(f"  • Origin: {record.origin.value}")
            console.print(f"  • Created: {record.created_at}")
            console.print(f"  • Updated: {record.updated_at}")
        elif isinstance(record, NoteRecord):
            console.print(f"[bold cyan]{record.id}[/bold cyan] [bold]{record.title}[/bold] [dim]({record.category})[/dim]")
            console.print(f"  • Note: {record.text}")
            console.print(f"  • Origin: {record.origin.value}")
            console.print(f"  • Created: {record.created_at}")
            console.print(f"  • Updated: {record.updated_at}")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Error retrieving record:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


@app.command(name="search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query string."),
    page: int = typer.Option(1, "--page", help="Page number for pagination (starts at 1)."),
    page_size: int = typer.Option(20, "--page-size", help="Number of items per page (default: 20)."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
):
    """Search project memory records using full-text search."""
    try:
        result = search_records(query, project_path=path, page=page, page_size=page_size)
        if not result.items:
            console.print(f"No results found for query: '{query}'")
            return

        total_pages = (result.total + result.page_size - 1) // result.page_size if result.total > 0 else 1
        console.print(f"[bold]Search results for:[/bold] '{result.query}' (Total: {result.total}, Page {result.page} of {total_pages})")

        for item in result.items:
            type_label = "[blue]decision[/blue]" if item.record_type == "decision" else "[magenta]note[/magenta]"
            console.print(f"  • [bold cyan]{item.id}[/bold cyan] ({type_label}) [bold]{item.title}[/bold] [{item.category}]")
            console.print(f"    {item.snippet}")
    except Exception as e:
        console.print(f"[bold red]Error searching records:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


@app.command(name="context")
def context_cmd(
    query: str = typer.Argument(..., help="Task description or query string to retrieve relevant context."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
):
    """Retrieve relevant project memory context (Decisions and Notes) for a task."""
    try:
        result = get_context(query, project_path=path)
        if json_output:
            console.print(result.model_dump_json(indent=2))
            return

        if not result.decisions and not result.notes:
            console.print(f"No relevant context found for: '{query}'")
            return

        console.print(f"[bold]Context for:[/bold] '{result.query}'")

        if result.decisions:
            console.print("\n[bold blue]Decisions:[/bold blue]")
            for d in result.decisions:
                console.print(f"  • [bold cyan]{d.id}[/bold cyan] [bold]{d.title}[/bold] [dim]({d.category})[/dim]")
                console.print(f"    Decision: {d.decision}")
                console.print(f"    Reason: {d.reason}")
                console.print(f"    Origin: {d.origin.value}")

        if result.notes:
            console.print("\n[bold magenta]Notes:[/bold magenta]")
            for n in result.notes:
                console.print(f"  • [bold cyan]{n.id}[/bold cyan] [bold]{n.title}[/bold] [dim]({n.category})[/dim]")
                console.print(f"    Text: {n.text}")
                console.print(f"    Origin: {n.origin.value}")
    except Exception as e:
        console.print(f"[bold red]Error retrieving context:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


@app.command(name="edit")
def edit_cmd(
    record_id: str = typer.Argument(..., help="ID of the record to edit (e.g. D-000001 or N-000001)."),
    title: str | None = typer.Option(None, "--title", help="New title."),
    category: str | None = typer.Option(None, "--category", help="New category."),
    decision: str | None = typer.Option(None, "--decision", help="New decision text (decisions only)."),
    reason: str | None = typer.Option(None, "--reason", help="New reason rationale (decisions only)."),
    text: str | None = typer.Option(None, "--text", help="New note text (notes only)."),
    origin: Origin | None = typer.Option(None, "--origin", help="New origin (live or bootstrap)."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
):
    """Edit an existing decision or note in project memory."""
    try:
        changes: dict[str, str | Origin] = {}
        if title is not None:
            changes["title"] = title
        if category is not None:
            changes["category"] = category
        if decision is not None:
            changes["decision"] = decision
        if reason is not None:
            changes["reason"] = reason
        if text is not None:
            changes["text"] = text
        if origin is not None:
            changes["origin"] = origin

        if not changes:
            console.print("[bold red]Error:[/bold red] No fields provided to edit. Provide at least one field to update.", highlight=False)
            raise typer.Exit(code=1)

        record = edit_record(record_id, changes, project_path=path)
        console.print(f"[bold green]✓[/bold green] Updated record [bold cyan]{record.id}[/bold cyan]: {record.title}")
        if isinstance(record, DecisionRecord):
            console.print(f"  • Category: {record.category}")
            console.print(f"  • Decision: {record.decision}")
            console.print(f"  • Reason: {record.reason}")
            console.print(f"  • Origin: {record.origin.value}")
            console.print(f"  • Updated at: {record.updated_at}")
        elif isinstance(record, NoteRecord):
            console.print(f"  • Category: {record.category}")
            console.print(f"  • Text: {record.text}")
            console.print(f"  • Origin: {record.origin.value}")
            console.print(f"  • Updated at: {record.updated_at}")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Error editing record:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


@app.command(name="delete")
def delete_cmd(
    record_id: str = typer.Argument(..., help="ID of the record to delete (e.g. D-000001 or N-000001)."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
):
    """Soft-delete an existing decision or note from project memory."""
    try:
        record = delete_record(record_id, project_path=path)
        rec_type = "decision" if isinstance(record, DecisionRecord) else "note"
        console.print(f"[bold green]✓[/bold green] Soft-deleted {rec_type} [bold cyan]{record.id}[/bold cyan]: {record.title}")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Error deleting record:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


@app.command(name="apply")
def apply_cmd(
    mutation_file: Path = typer.Argument(..., help="Path to JSON file containing batch mutations."),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Project path (defaults to current directory)."),
):
    """Apply a batch of mutations atomically from a JSON file."""
    try:
        result = apply_batch(mutation_file, project_path=path)
        console.print(f"[bold green]✓[/bold green] Successfully applied [bold]{result.applied}[/bold] batch operations.")
        for rec in result.records:
            status_desc = "deleted" if rec.deleted_at is not None else "updated/created"
            console.print(f"  • [bold cyan]{rec.id}[/bold cyan]: {rec.title} ({status_desc})")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]Error applying batch:[/bold red] {e}", highlight=False)
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    app()

