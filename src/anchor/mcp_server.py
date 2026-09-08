"""Official MCP Server implementation for Anchor."""

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from anchor import __version__
from anchor.core import (
    add_decision,
    add_note,
    apply_batch,
    complete_bootstrap,
    delete_record,
    edit_record,
    get_context,
    get_project_status,
    get_record,
    search_records,
)
from anchor.models import DecisionInput, NoteInput, Origin


def create_mcp_server() -> MCPServer:
    """Create and configure the Anchor MCP server instance."""
    server = MCPServer(
        name="anchor",
        version=__version__,
        description="Anchor: Local project-memory and decision system for agentic software development.",
    )

    @server.tool(
        name="anchor_status",
        description="Get current Anchor status for the project at the given path (defaults to current directory).",
    )
    def handle_status(path: str = ".") -> dict[str, Any]:
        """Get the current Anchor status for a project."""
        try:
            return get_project_status(Path(path))
        except Exception as e:
            raise ToolError(f"Error getting project status: {e}") from e

    @server.tool(
        name="anchor_search",
        description="Search project memory records (decisions and notes) using full-text search.",
    )
    def handle_search(
        query: str,
        path: str = ".",
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Search project memory records."""
        try:
            res = search_records(
                query=query,
                project_path=Path(path),
                page=page,
                page_size=page_size,
                include_deleted=include_deleted,
            )
            return res.model_dump()
        except Exception as e:
            raise ToolError(f"Error searching records: {e}") from e

    @server.tool(
        name="anchor_context",
        description="Retrieve task-oriented context (full Decisions and Notes) relevant to a task query.",
    )
    def handle_context(
        query: str,
        path: str = ".",
        include_deleted: bool = False,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Retrieve relevant project memory context for a task."""
        try:
            res = get_context(
                query=query,
                project_path=Path(path),
                include_deleted=include_deleted,
                limit=limit,
            )
            return res.model_dump()
        except Exception as e:
            raise ToolError(f"Error retrieving context: {e}") from e

    @server.tool(
        name="anchor_get",
        description="Retrieve a Decision or Note record by its stable ID (e.g. D-000001 or N-000001).",
    )
    def handle_get(
        id: str,
        path: str = ".",
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Retrieve a project memory record by ID."""
        try:
            rec = get_record(record_id=id, project_path=Path(path), include_deleted=include_deleted)
            if rec is None:
                raise ToolError(f"Record '{id}' not found.")
            return rec.model_dump()
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"Error retrieving record: {e}") from e

    @server.tool(
        name="anchor_add_decision",
        description="Add a persistent decision record to project memory.",
    )
    def handle_add_decision(
        title: str,
        category: str,
        decision: str,
        reason: str,
        origin: str = "live",
        path: str = ".",
    ) -> dict[str, Any]:
        """Add a new decision to project memory."""
        try:
            origin_enum = Origin(origin.lower().strip())
            input_data = DecisionInput(
                title=title,
                category=category,
                decision=decision,
                reason=reason,
                origin=origin_enum,
            )
            rec = add_decision(input_data, project_path=Path(path))
            return rec.model_dump()
        except Exception as e:
            raise ToolError(f"Error adding decision: {e}") from e

    @server.tool(
        name="anchor_add_note",
        description="Add a persistent note record to project memory.",
    )
    def handle_add_note(
        title: str,
        category: str,
        text: str,
        origin: str = "live",
        path: str = ".",
    ) -> dict[str, Any]:
        """Add a new note to project memory."""
        try:
            origin_enum = Origin(origin.lower().strip())
            input_data = NoteInput(
                title=title,
                category=category,
                text=text,
                origin=origin_enum,
            )
            rec = add_note(input_data, project_path=Path(path))
            return rec.model_dump()
        except Exception as e:
            raise ToolError(f"Error adding note: {e}") from e

    @server.tool(
        name="anchor_edit",
        description="Edit an existing decision or note record in project memory.",
    )
    def handle_edit(
        id: str,
        title: str | None = None,
        category: str | None = None,
        decision: str | None = None,
        reason: str | None = None,
        text: str | None = None,
        origin: str | None = None,
        path: str = ".",
    ) -> dict[str, Any]:
        """Edit an existing decision or note in project memory."""
        try:
            changes: dict[str, Any] = {}
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
                changes["origin"] = Origin(origin.lower().strip())

            if not changes:
                raise ToolError("No fields provided to edit. Provide at least one field to update.")

            rec = edit_record(id, changes, project_path=Path(path))
            return rec.model_dump()
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"Error editing record: {e}") from e

    @server.tool(
        name="anchor_delete",
        description="Soft-delete an existing decision or note record from project memory.",
    )
    def handle_delete(
        id: str,
        path: str = ".",
    ) -> dict[str, Any]:
        """Soft-delete an existing record."""
        try:
            rec = delete_record(id, project_path=Path(path))
            return rec.model_dump()
        except Exception as e:
            raise ToolError(f"Error deleting record: {e}") from e

    @server.tool(
        name="anchor_apply_batch",
        description="Apply a batch of mutations (edits, deletes, adds) atomically within a single transaction.",
    )
    def handle_apply_batch(
        operations: list[dict[str, Any]],
        path: str = ".",
    ) -> dict[str, Any]:
        """Apply atomic batch of memory mutations."""
        try:
            batch_input = {"operations": operations}
            res = apply_batch(batch_input, project_path=Path(path))
            return res.model_dump()
        except Exception as e:
            raise ToolError(f"Error applying batch: {e}") from e

    @server.tool(
        name="anchor_complete_bootstrap",
        description="Explicitly complete the existing-project bootstrap lifecycle.",
    )
    def handle_complete_bootstrap(
        path: str = ".",
    ) -> dict[str, Any]:
        """Complete project bootstrap lifecycle."""
        try:
            return complete_bootstrap(project_path=Path(path))
        except Exception as e:
            raise ToolError(f"Error completing bootstrap: {e}") from e

    return server


def run_mcp_server() -> None:
    """Run the Anchor MCP server over STDIO transport."""
    server = create_mcp_server()
    server.run(transport="stdio")
