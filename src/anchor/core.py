"""Core domain logic for Anchor operations."""

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anchor.db import init_database
from anchor.models import (
    DecisionInput,
    DecisionRecord,
    NoteInput,
    NoteRecord,
    Origin,
    RecordType,
    SearchResult,
    SearchResultItem,
)
from anchor.templates import ANCHOR_BLOCK_END, ANCHOR_BLOCK_START, ANCHOR_FULL_BLOCK


def find_project_root(start_path: Path = Path(".")) -> Path | None:
    """Find the root directory of an Anchor project by searching upward for .anchor/anchor.db."""
    current = start_path.resolve()
    for directory in [current, *current.parents]:
        if (directory / ".anchor" / "anchor.db").is_file():
            return directory
    return None


def get_project_status(project_path: Path = Path(".")) -> dict[str, Any]:
    """
    Get current Anchor status for the project at project_path.
    Returns status dictionary including initialization state, metadata, and record counts.
    """
    resolved = project_path.resolve()
    root = find_project_root(resolved)
    
    if not root:
        return {
            "project": str(resolved),
            "initialized": False,
        }
        
    db_path = root / ".anchor" / "anchor.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM metadata")
        metadata = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(*) FROM decisions WHERE deleted_at IS NULL")
        decisions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM notes WHERE deleted_at IS NULL")
        notes_count = cursor.fetchone()[0]
        
    return {
        "project": str(root),
        "initialized": True,
        "project_type": metadata.get("project_type", "unknown"),
        "bootstrap_status": metadata.get("bootstrap_status", "none"),
        "decisions": decisions_count,
        "notes": notes_count,
    }


def add_decision(input_data: DecisionInput, project_path: Path = Path(".")) -> DecisionRecord:
    """
    Transactionally insert a new decision record and its FTS entry.
    Generates deterministic sequential ID (D-000001) and UTC timestamps.
    Rejects duplicate active records with identical content.
    """
    resolved = project_path.resolve()
    root = find_project_root(resolved)
    if not root:
        raise ValueError(f"Project at '{resolved}' is not initialized with Anchor. Run 'anchor init' first.")

    db_path = root / ".anchor" / "anchor.db"
    now_iso = datetime.now(UTC).isoformat()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check for active duplicate decision
        cursor.execute(
            """
            SELECT id FROM decisions
            WHERE deleted_at IS NULL
              AND title = ?
              AND category = ?
              AND decision = ?
              AND reason = ?
            """,
            (input_data.title, input_data.category, input_data.decision, input_data.reason),
        )
        dup = cursor.fetchone()
        if dup:
            raise ValueError(f"Duplicate decision: an active decision with identical content already exists ({dup[0]}).")

        cursor.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM decisions")
        next_seq = cursor.fetchone()[0]
        decision_id = f"D-{next_seq:06d}"

        cursor.execute(
            """
            INSERT INTO decisions (id, seq, title, category, decision, reason, origin, created_at, updated_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                decision_id,
                next_seq,
                input_data.title,
                input_data.category,
                input_data.decision,
                input_data.reason,
                input_data.origin.value,
                now_iso,
                now_iso,
            ),
        )

        cursor.execute(
            """
            INSERT INTO anchor_fts (id, record_type, title, category, content, reason)
            VALUES (?, 'decision', ?, ?, ?, ?)
            """,
            (
                decision_id,
                input_data.title,
                input_data.category,
                input_data.decision,
                input_data.reason,
            ),
        )
        conn.commit()

    return DecisionRecord(
        id=decision_id,
        seq=next_seq,
        title=input_data.title,
        category=input_data.category,
        decision=input_data.decision,
        reason=input_data.reason,
        origin=input_data.origin,
        created_at=now_iso,
        updated_at=now_iso,
        deleted_at=None,
    )


def add_note(input_data: NoteInput, project_path: Path = Path(".")) -> NoteRecord:
    """
    Transactionally insert a new note record and its FTS entry.
    Generates deterministic sequential ID (N-000001) and UTC timestamps.
    Rejects duplicate active records with identical content.
    """
    resolved = project_path.resolve()
    root = find_project_root(resolved)
    if not root:
        raise ValueError(f"Project at '{resolved}' is not initialized with Anchor. Run 'anchor init' first.")

    db_path = root / ".anchor" / "anchor.db"
    now_iso = datetime.now(UTC).isoformat()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Check for active duplicate note
        cursor.execute(
            """
            SELECT id FROM notes
            WHERE deleted_at IS NULL
              AND title = ?
              AND category = ?
              AND text = ?
            """,
            (input_data.title, input_data.category, input_data.text),
        )
        dup = cursor.fetchone()
        if dup:
            raise ValueError(f"Duplicate note: an active note with identical content already exists ({dup[0]}).")

        cursor.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM notes")
        next_seq = cursor.fetchone()[0]
        note_id = f"N-{next_seq:06d}"

        cursor.execute(
            """
            INSERT INTO notes (id, seq, title, category, text, origin, created_at, updated_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                note_id,
                next_seq,
                input_data.title,
                input_data.category,
                input_data.text,
                input_data.origin.value,
                now_iso,
                now_iso,
            ),
        )

        cursor.execute(
            """
            INSERT INTO anchor_fts (id, record_type, title, category, content, reason)
            VALUES (?, 'note', ?, ?, ?, '')
            """,
            (
                note_id,
                input_data.title,
                input_data.category,
                input_data.text,
            ),
        )
        conn.commit()

    return NoteRecord(
        id=note_id,
        seq=next_seq,
        title=input_data.title,
        category=input_data.category,
        text=input_data.text,
        origin=input_data.origin,
        created_at=now_iso,
        updated_at=now_iso,
        deleted_at=None,
    )


def update_or_create_doc_file(file_path: Path) -> None:
    """
    Update or create a documentation file (AGENTS.md / CLAUDE.md)
    ensuring only the Anchor-managed block is replaced or added,
    leaving any other content untouched.
    """
    if not file_path.exists():
        file_path.write_text(ANCHOR_FULL_BLOCK, encoding="utf-8")
        return

    content = file_path.read_text(encoding="utf-8")
    
    # Pattern to match existing anchor block
    pattern = re.compile(
        rf"{re.escape(ANCHOR_BLOCK_START)}.*?{re.escape(ANCHOR_BLOCK_END)}",
        re.DOTALL,
    )
    
    if pattern.search(content):
        # Replace existing block
        new_content = pattern.sub(ANCHOR_FULL_BLOCK.strip(), content)
    else:
        # Append anchor block if not present
        if content.strip():
            new_content = f"{content.rstrip()}\n\n{ANCHOR_FULL_BLOCK}"
        else:
            new_content = ANCHOR_FULL_BLOCK

    file_path.write_text(new_content, encoding="utf-8")


def is_directory_existing_project(project_path: Path) -> bool:
    """Check if the directory contains files indicating an existing project."""
    ignored = {".git", ".anchor", "AGENTS.md", "CLAUDE.md", ".DS_Store", "Thumbs.db"}
    try:
        for item in project_path.iterdir():
            if item.name not in ignored:
                return True
    except FileNotFoundError:
        return False
    return False


def initialize_project(project_path: Path) -> dict[str, Any]:
    """
    Initialize an Anchor project at the given path.
    Creates .anchor/anchor.db, .anchor/.gitignore, AGENTS.md, CLAUDE.md, and initializes metadata.
    """
    project_path = project_path.resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    
    anchor_dir = project_path / ".anchor"
    anchor_dir.mkdir(parents=True, exist_ok=True)
    
    gitignore_path = anchor_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text("*\n", encoding="utf-8")
        
    db_path = anchor_dir / "anchor.db"
    
    is_existing = is_directory_existing_project(project_path)
    
    # Initialize SQLite database
    init_database(db_path, is_existing_project=is_existing)
    
    # Create or update AGENTS.md and CLAUDE.md
    update_or_create_doc_file(project_path / "AGENTS.md")
    update_or_create_doc_file(project_path / "CLAUDE.md")
        
    mcp_config = {
        "mcpServers": {
            "anchor": {
                "command": "anchor",
                "args": [
                    "mcp"
                ]
            }
        }
    }
    
    return {
        "project_path": str(project_path),
        "db_path": str(db_path),
        "is_existing": is_existing,
        "mcp_config": mcp_config,
    }


def get_record(
    record_id: str,
    project_path: Path = Path("."),
    include_deleted: bool = False,
) -> DecisionRecord | NoteRecord | None:
    """
    Retrieve a Decision or Note record by its stable ID.
    Returns None if not found or if the record is soft-deleted (unless include_deleted=True).
    Raises ValueError if project is uninitialized.
    """
    resolved = project_path.resolve()
    root = find_project_root(resolved)
    if not root:
        raise ValueError(f"Project at '{resolved}' is not initialized with Anchor. Run 'anchor init' first.")

    db_path = root / ".anchor" / "anchor.db"

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        if record_id.startswith("D-"):
            cursor.execute(
                """
                SELECT id, seq, title, category, decision, reason, origin, created_at, updated_at, deleted_at
                FROM decisions
                WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                if row[9] is not None and not include_deleted:
                    return None
                return DecisionRecord(
                    id=row[0],
                    seq=row[1],
                    title=row[2],
                    category=row[3],
                    decision=row[4],
                    reason=row[5],
                    origin=Origin(row[6]),
                    created_at=row[7],
                    updated_at=row[8],
                    deleted_at=row[9],
                )
        elif record_id.startswith("N-"):
            cursor.execute(
                """
                SELECT id, seq, title, category, text, origin, created_at, updated_at, deleted_at
                FROM notes
                WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                if row[8] is not None and not include_deleted:
                    return None
                return NoteRecord(
                    id=row[0],
                    seq=row[1],
                    title=row[2],
                    category=row[3],
                    text=row[4],
                    origin=Origin(row[5]),
                    created_at=row[6],
                    updated_at=row[7],
                    deleted_at=row[8],
                )
        else:
            # Check decisions first, then notes
            cursor.execute(
                """
                SELECT id, seq, title, category, decision, reason, origin, created_at, updated_at, deleted_at
                FROM decisions
                WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                if row[9] is not None and not include_deleted:
                    return None
                return DecisionRecord(
                    id=row[0],
                    seq=row[1],
                    title=row[2],
                    category=row[3],
                    decision=row[4],
                    reason=row[5],
                    origin=Origin(row[6]),
                    created_at=row[7],
                    updated_at=row[8],
                    deleted_at=row[9],
                )

            cursor.execute(
                """
                SELECT id, seq, title, category, text, origin, created_at, updated_at, deleted_at
                FROM notes
                WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                if row[8] is not None and not include_deleted:
                    return None
                return NoteRecord(
                    id=row[0],
                    seq=row[1],
                    title=row[2],
                    category=row[3],
                    text=row[4],
                    origin=Origin(row[5]),
                    created_at=row[6],
                    updated_at=row[7],
                    deleted_at=row[8],
                )

    return None


def sanitize_fts_query(query: str) -> str:
    """
    Sanitize and prepare a query string for safe FTS5 execution.
    Extracts tokens and creates prefix-matching quoted tokens to prevent syntax errors.
    Returns empty string if no valid search tokens are found.
    """
    if not query or not query.strip():
        return ""

    tokens = re.findall(r"[a-zA-Z0-9_\u0080-\uffff]+", query)
    if not tokens:
        return ""

    # Quote each token and add prefix wildcard
    escaped_tokens = [f'"{token.replace("\"", "\"\"")}"*' for token in tokens]
    return " ".join(escaped_tokens)


def _make_snippet(text: str, max_len: int = 120) -> str:
    """Create a single-line compact snippet from multiline text."""
    collapsed = " ".join(text.split())
    if len(collapsed) > max_len:
        return collapsed[: max_len - 3] + "..."
    return collapsed


def search_records(
    query: str,
    project_path: Path = Path("."),
    page: int = 1,
    page_size: int = 20,
    include_deleted: bool = False,
) -> SearchResult:
    """
    Search Anchor memory records using SQLite FTS5 with deterministic ranking,
    pagination, and soft-delete filtering.
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    resolved = project_path.resolve()
    root = find_project_root(resolved)
    if not root:
        raise ValueError(f"Project at '{resolved}' is not initialized with Anchor. Run 'anchor init' first.")

    sanitized = sanitize_fts_query(query)
    if not sanitized:
        return SearchResult(
            query=query,
            total=0,
            page=page,
            page_size=page_size,
            items=[],
        )

    db_path = root / ".anchor" / "anchor.db"
    include_del_int = 1 if include_deleted else 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Count total matching records
        count_sql = """
        SELECT COUNT(*)
        FROM anchor_fts(?) f
        LEFT JOIN decisions d ON f.id = d.id AND f.record_type = 'decision'
        LEFT JOIN notes n ON f.id = n.id AND f.record_type = 'note'
        WHERE (
            (f.record_type = 'decision' AND d.id IS NOT NULL AND (d.deleted_at IS NULL OR ? = 1))
            OR
            (f.record_type = 'note' AND n.id IS NOT NULL AND (n.deleted_at IS NULL OR ? = 1))
        )
        """
        cursor.execute(count_sql, (sanitized, include_del_int, include_del_int))
        total_count = cursor.fetchone()[0]

        offset = (page - 1) * page_size

        select_sql = """
        SELECT
            f.id,
            f.record_type,
            f.title,
            f.category,
            COALESCE(d.decision, n.text, f.content) AS body,
            COALESCE(d.origin, n.origin, 'live') AS origin,
            COALESCE(d.created_at, n.created_at, '') AS created_at
        FROM anchor_fts(?) f
        LEFT JOIN decisions d ON f.id = d.id AND f.record_type = 'decision'
        LEFT JOIN notes n ON f.id = n.id AND f.record_type = 'note'
        WHERE (
            (f.record_type = 'decision' AND d.id IS NOT NULL AND (d.deleted_at IS NULL OR ? = 1))
            OR
            (f.record_type = 'note' AND n.id IS NOT NULL AND (n.deleted_at IS NULL OR ? = 1))
        )
        ORDER BY f.rank ASC, COALESCE(d.created_at, n.created_at) DESC, f.id ASC
        LIMIT ? OFFSET ?
        """
        cursor.execute(select_sql, (sanitized, include_del_int, include_del_int, page_size, offset))

        rows = cursor.fetchall()

        items = [
            SearchResultItem(
                id=row[0],
                record_type=RecordType(row[1]),
                title=row[2],
                category=row[3],
                snippet=_make_snippet(row[4]),
                origin=Origin(row[5]),
                created_at=row[6],
            )
            for row in rows
        ]

    return SearchResult(
        query=query,
        total=total_count,
        page=page,
        page_size=page_size,
        items=items,
    )

