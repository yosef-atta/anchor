import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anchor.cli import app
from anchor.core import (
    add_decision,
    add_note,
    get_context,
    initialize_project,
)
from anchor.models import (
    ContextResult,
    DecisionInput,
    DecisionRecord,
    NoteInput,
    NoteRecord,
    Origin,
)

runner = CliRunner()


def test_context_relevant_decision_retrieval(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    # Seed decisions
    add_decision(
        DecisionInput(
            title="Primary database engine",
            category="database",
            decision="Adopt PostgreSQL with pgvector extension.",
            reason="Required for relational schema and vector embeddings.",
            origin=Origin.LIVE,
        ),
        project_path=target_dir,
    )
    add_decision(
        DecisionInput(
            title="Authentication cookies",
            category="auth",
            decision="Use HTTP-only secure cookies for session storage.",
            reason="Protect session identifiers against XSS token extraction.",
            origin=Origin.LIVE,
        ),
        project_path=target_dir,
    )
    # Seed unrelated note
    add_note(
        NoteInput(
            title="Dev server frontend port",
            category="frontend",
            text="Frontend Vite dev server runs on port 5173.",
            origin=Origin.BOOTSTRAP,
        ),
        project_path=target_dir,
    )

    # Query for database decision
    result = get_context("PostgreSQL database", project_path=target_dir)
    assert isinstance(result, ContextResult)
    assert result.query == "PostgreSQL database"
    assert len(result.decisions) == 1
    assert len(result.notes) == 0

    dec = result.decisions[0]
    assert isinstance(dec, DecisionRecord)
    assert dec.id == "D-000001"
    assert dec.seq == 1
    assert dec.title == "Primary database engine"
    assert dec.category == "database"
    assert dec.decision == "Adopt PostgreSQL with pgvector extension."
    assert dec.reason == "Required for relational schema and vector embeddings."
    assert dec.origin == Origin.LIVE
    assert dec.created_at != ""
    assert dec.updated_at != ""
    assert dec.deleted_at is None


def test_context_relevant_note_retrieval(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="Package manager",
            category="tooling",
            decision="Use pnpm for package management.",
            reason="Fast, disk-efficient dependency deduplication.",
            origin=Origin.LIVE,
        ),
        project_path=target_dir,
    )
    add_note(
        NoteInput(
            title="Stripe webhook tunneling",
            category="payments",
            text="Stripe test webhooks require local tunnel via stripe listen --forward-to localhost:8000/webhook.",
            origin=Origin.BOOTSTRAP,
        ),
        project_path=target_dir,
    )

    result = get_context("Stripe webhook", project_path=target_dir)
    assert isinstance(result, ContextResult)
    assert result.query == "Stripe webhook"
    assert len(result.decisions) == 0
    assert len(result.notes) == 1

    note = result.notes[0]
    assert isinstance(note, NoteRecord)
    assert note.id == "N-000001"
    assert note.seq == 1
    assert note.title == "Stripe webhook tunneling"
    assert note.category == "payments"
    assert "stripe listen --forward-to" in note.text
    assert note.origin == Origin.BOOTSTRAP
    assert note.created_at != ""
    assert note.updated_at != ""
    assert note.deleted_at is None


def test_context_mixed_results(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    # Decision mentioning Redis
    add_decision(
        DecisionInput(
            title="Redis caching layer",
            category="caching",
            decision="Use Redis for server-side cache and session invalidation.",
            reason="Sub-millisecond latency for hot key-value lookups.",
            origin=Origin.LIVE,
        ),
        project_path=target_dir,
    )
    # Note mentioning Redis
    add_note(
        NoteInput(
            title="Redis local port",
            category="infrastructure",
            text="Local Redis runs via docker compose on port 6379 with standard auth.",
            origin=Origin.BOOTSTRAP,
        ),
        project_path=target_dir,
    )
    # Unrelated note
    add_note(
        NoteInput(
            title="Linting rule",
            category="code-quality",
            text="Ruff line length is configured to 120 chars.",
            origin=Origin.LIVE,
        ),
        project_path=target_dir,
    )

    result = get_context("Redis", project_path=target_dir)
    assert len(result.decisions) == 1
    assert len(result.notes) == 1
    assert result.decisions[0].id == "D-000001"
    assert result.notes[0].id == "N-000001"


def test_context_empty_and_no_match(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="Primary database",
            category="database",
            decision="Use PostgreSQL.",
            reason="Required for pgvector.",
        ),
        project_path=target_dir,
    )

    # Term not in database
    res_none = get_context("Elasticsearch cluster", project_path=target_dir)
    assert isinstance(res_none, ContextResult)
    assert res_none.decisions == []
    assert res_none.notes == []

    # Empty string
    res_empty = get_context("", project_path=target_dir)
    assert res_empty.decisions == []
    assert res_empty.notes == []

    # Whitespace query
    res_ws = get_context("    \t\n  ", project_path=target_dir)
    assert res_ws.decisions == []
    assert res_ws.notes == []

    # Malformed queries with special characters
    malformed = ['"""', "AND OR NOT ()", "::: ;;;", "***", "((((("]
    for mq in malformed:
        res_malformed = get_context(mq, project_path=target_dir)
        assert isinstance(res_malformed, ContextResult)
        assert isinstance(res_malformed.decisions, list)
        assert isinstance(res_malformed.notes, list)


def test_context_stable_response_structure(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="Database engine",
            category="database",
            decision="Use PostgreSQL.",
            reason="Need relational transactions.",
        ),
        project_path=target_dir,
    )
    add_note(
        NoteInput(
            title="Database host",
            category="database",
            text="Host is localhost:5432.",
        ),
        project_path=target_dir,
    )

    res = get_context("database", project_path=target_dir)
    dumped = res.model_dump()

    assert "query" in dumped
    assert "decisions" in dumped
    assert "notes" in dumped
    assert dumped["query"] == "database"
    assert len(dumped["decisions"]) == 1
    assert len(dumped["notes"]) == 1

    # Check decision record structure keys
    decision_keys = set(dumped["decisions"][0].keys())
    assert decision_keys == {
        "id",
        "seq",
        "title",
        "category",
        "decision",
        "reason",
        "origin",
        "created_at",
        "updated_at",
        "deleted_at",
    }

    # Check note record structure keys
    note_keys = set(dumped["notes"][0].keys())
    assert note_keys == {
        "id",
        "seq",
        "title",
        "category",
        "text",
        "origin",
        "created_at",
        "updated_at",
        "deleted_at",
    }

    # Verify JSON serialization round-trip
    json_str = res.model_dump_json()
    parsed = json.loads(json_str)
    reconstituted = ContextResult.model_validate(parsed)
    assert reconstituted == res


def test_context_soft_deleted_records_excluded_by_default(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="Redis caching",
            category="caching",
            decision="Use Redis for session store.",
            reason="Low latency key-value caching.",
        ),
        project_path=target_dir,
    )
    add_note(
        NoteInput(
            title="Redis port",
            category="infrastructure",
            text="Redis is listening on 6379.",
        ),
        project_path=target_dir,
    )

    # Soft-delete decision and note directly in DB
    db_path = target_dir / ".anchor" / "anchor.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE decisions SET deleted_at = '2026-09-08T00:00:00Z' WHERE id = 'D-000001'")
        conn.execute("UPDATE notes SET deleted_at = '2026-09-08T00:00:00Z' WHERE id = 'N-000001'")
        conn.commit()

    # Default excludes deleted
    res_default = get_context("Redis", project_path=target_dir)
    assert len(res_default.decisions) == 0
    assert len(res_default.notes) == 0

    # Explicit include_deleted=True includes them
    res_all = get_context("Redis", project_path=target_dir, include_deleted=True)
    assert len(res_all.decisions) == 1
    assert len(res_all.notes) == 1
    assert res_all.decisions[0].deleted_at == "2026-09-08T00:00:00Z"
    assert res_all.notes[0].deleted_at == "2026-09-08T00:00:00Z"


def test_cli_context(tmp_path: Path):
    target_dir = tmp_path / "proj"
    runner.invoke(app, ["init", str(target_dir)])

    runner.invoke(
        app,
        [
            "add",
            "decision",
            "--title",
            "Primary database",
            "--category",
            "database",
            "--decision",
            "Use PostgreSQL.",
            "--reason",
            "Required for JSONB.",
            "-p",
            str(target_dir),
        ],
    )
    runner.invoke(
        app,
        [
            "add",
            "note",
            "--title",
            "Dev database port",
            "--category",
            "database",
            "--text",
            "PostgreSQL runs on port 5432.",
            "-p",
            str(target_dir),
        ],
    )

    # Standard human-readable CLI output
    res = runner.invoke(app, ["context", "database", "-p", str(target_dir)])
    assert res.exit_code == 0
    assert "Context for: 'database'" in res.output
    assert "Decisions:" in res.output
    assert "D-000001" in res.output
    assert "Use PostgreSQL." in res.output
    assert "Notes:" in res.output
    assert "N-000001" in res.output
    assert "PostgreSQL runs on port 5432." in res.output

    # JSON formatted CLI output
    res_json = runner.invoke(app, ["context", "database", "--json", "-p", str(target_dir)])
    assert res_json.exit_code == 0
    parsed = json.loads(res_json.output)
    assert parsed["query"] == "database"
    assert len(parsed["decisions"]) == 1
    assert len(parsed["notes"]) == 1
    assert parsed["decisions"][0]["id"] == "D-000001"
    assert parsed["notes"][0]["id"] == "N-000001"

    # No match output
    res_nomatch = runner.invoke(app, ["context", "nonexistentterm", "-p", str(target_dir)])
    assert res_nomatch.exit_code == 0
    assert "No relevant context found" in res_nomatch.output


def test_cli_context_uninitialized_project_fails(tmp_path: Path):
    uninit_dir = tmp_path / "uninit"
    uninit_dir.mkdir()

    with pytest.raises(ValueError, match="not initialized"):
        get_context("test", project_path=uninit_dir)

    res = runner.invoke(app, ["context", "test", "-p", str(uninit_dir)])
    assert res.exit_code != 0
    assert "Error retrieving context:" in res.output
