import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anchor.cli import app
from anchor.core import add_decision, add_note, initialize_project
from anchor.models import DecisionInput, NoteInput, Origin

runner = CliRunner()


def test_add_decision_valid(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    inp = DecisionInput(
        title="Primary database",
        category="database",
        decision="Use PostgreSQL.",
        reason="Required for JSONB and pgvector.",
    )
    record = add_decision(inp, project_path=target_dir)

    assert record.id == "D-000001"
    assert record.seq == 1
    assert record.title == "Primary database"
    assert record.category == "database"
    assert record.decision == "Use PostgreSQL."
    assert record.reason == "Required for JSONB and pgvector."
    assert record.origin == Origin.LIVE
    assert record.created_at == record.updated_at
    # Validate ISO timestamp
    datetime.fromisoformat(record.created_at)

    # Check database table directly
    db_path = target_dir / ".anchor" / "anchor.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, seq, title, category, decision, reason, origin, created_at, updated_at, deleted_at FROM decisions WHERE id = 'D-000001'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "D-000001"
        assert row[1] == 1
        assert row[2] == "Primary database"
        assert row[3] == "database"
        assert row[4] == "Use PostgreSQL."
        assert row[5] == "Required for JSONB and pgvector."
        assert row[6] == "live"
        assert row[7] == record.created_at
        assert row[8] == record.updated_at
        assert row[9] is None

        # Check FTS entry
        cursor.execute("SELECT id, record_type, title, category, content, reason FROM anchor_fts WHERE id = 'D-000001'")
        fts_row = cursor.fetchone()
        assert fts_row is not None
        assert fts_row[0] == "D-000001"
        assert fts_row[1] == "decision"
        assert fts_row[2] == "Primary database"
        assert fts_row[3] == "database"
        assert fts_row[4] == "Use PostgreSQL."
        assert fts_row[5] == "Required for JSONB and pgvector."


def test_add_note_valid(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    inp = NoteInput(
        title="Local database",
        category="development",
        text="PostgreSQL runs through Docker Compose on port 5432.",
        origin=Origin.BOOTSTRAP,
    )
    record = add_note(inp, project_path=target_dir)

    assert record.id == "N-000001"
    assert record.seq == 1
    assert record.title == "Local database"
    assert record.category == "development"
    assert record.text == "PostgreSQL runs through Docker Compose on port 5432."
    assert record.origin == Origin.BOOTSTRAP
    assert record.created_at == record.updated_at
    datetime.fromisoformat(record.created_at)

    db_path = target_dir / ".anchor" / "anchor.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, seq, title, category, text, origin, created_at, updated_at, deleted_at FROM notes WHERE id = 'N-000001'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "N-000001"
        assert row[1] == 1
        assert row[2] == "Local database"
        assert row[3] == "development"
        assert row[4] == "PostgreSQL runs through Docker Compose on port 5432."
        assert row[5] == "bootstrap"
        assert row[6] == record.created_at
        assert row[7] == record.updated_at
        assert row[8] is None

        cursor.execute("SELECT id, record_type, title, category, content, reason FROM anchor_fts WHERE id = 'N-000001'")
        fts_row = cursor.fetchone()
        assert fts_row is not None
        assert fts_row[0] == "N-000001"
        assert fts_row[1] == "note"
        assert fts_row[2] == "Local database"
        assert fts_row[3] == "development"
        assert fts_row[4] == "PostgreSQL runs through Docker Compose on port 5432."
        assert fts_row[5] == ""


def test_id_sequencing(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    d1 = add_decision(DecisionInput(title="T1", category="c", decision="d1", reason="r1"), project_path=target_dir)
    d2 = add_decision(DecisionInput(title="T2", category="c", decision="d2", reason="r2"), project_path=target_dir)
    d3 = add_decision(DecisionInput(title="T3", category="c", decision="d3", reason="r3"), project_path=target_dir)

    assert d1.id == "D-000001" and d1.seq == 1
    assert d2.id == "D-000002" and d2.seq == 2
    assert d3.id == "D-000003" and d3.seq == 3

    n1 = add_note(NoteInput(title="N1", category="c", text="t1"), project_path=target_dir)
    n2 = add_note(NoteInput(title="N2", category="c", text="t2"), project_path=target_dir)

    assert n1.id == "N-000001" and n1.seq == 1
    assert n2.id == "N-000002" and n2.seq == 2


def test_required_fields_validation():
    with pytest.raises(ValueError):
        DecisionInput(title="", category="cat", decision="dec", reason="reason")

    with pytest.raises(ValueError):
        DecisionInput(title="title", category="   ", decision="dec", reason="reason")

    with pytest.raises(ValueError):
        DecisionInput(title="title", category="cat", decision="", reason="reason")

    with pytest.raises(ValueError):
        DecisionInput(title="title", category="cat", decision="dec", reason="  ")

    with pytest.raises(ValueError):
        NoteInput(title="", category="cat", text="text")

    with pytest.raises(ValueError):
        NoteInput(title="title", category="cat", text="   ")


def test_uninitialized_project_fails(tmp_path: Path):
    uninit_dir = tmp_path / "uninit"
    uninit_dir.mkdir()

    with pytest.raises(ValueError, match="not initialized"):
        add_decision(
            DecisionInput(title="T", category="C", decision="D", reason="R"),
            project_path=uninit_dir,
        )


def test_transaction_rollback_on_failure(tmp_path: Path, monkeypatch):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    db_path = target_dir / ".anchor" / "anchor.db"

    # Break FTS table schema to force an operational error during FTS insert
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE anchor_fts")
        conn.execute("CREATE TABLE anchor_fts (unrelated TEXT NOT NULL)")
        conn.commit()

    inp = DecisionInput(title="T", category="C", decision="D", reason="R")

    with pytest.raises(sqlite3.OperationalError):
        add_decision(inp, project_path=target_dir)

    # Check that decisions table remains empty because the transaction was rolled back
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM decisions")
        count = cursor.fetchone()[0]
        assert count == 0


def test_cli_add_decision_and_note(tmp_path: Path):
    target_dir = tmp_path / "proj"
    runner.invoke(app, ["init", str(target_dir)])

    # CLI add decision
    res = runner.invoke(
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
            "--origin",
            "live",
            "-p",
            str(target_dir),
        ],
    )
    assert res.exit_code == 0
    assert "Added decision D-000001: Primary database" in res.output

    # CLI add note
    res = runner.invoke(
        app,
        [
            "add",
            "note",
            "--title",
            "Dev port",
            "--category",
            "dev",
            "--text",
            "Port 3000",
            "--origin",
            "bootstrap",
            "-p",
            str(target_dir),
        ],
    )
    assert res.exit_code == 0
    assert "Added note N-000001: Dev port" in res.output

    # CLI status reflects additions
    status_res = runner.invoke(app, ["status", str(target_dir)])
    assert status_res.exit_code == 0
    assert "decisions: 1" in status_res.output
    assert "notes: 1" in status_res.output


def test_cli_validation_errors(tmp_path: Path):
    target_dir = tmp_path / "proj"
    runner.invoke(app, ["init", str(target_dir)])

    # Missing required argument
    res = runner.invoke(app, ["add", "decision", "--title", "T", "-p", str(target_dir)])
    assert res.exit_code != 0

    # Empty string validation error
    res = runner.invoke(
        app,
        [
            "add",
            "decision",
            "--title",
            "   ",
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
    assert res.exit_code != 0
    assert "Error adding decision" in res.output


def test_duplicate_decision_rejected(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    inp = DecisionInput(
        title="Primary database",
        category="database",
        decision="Use PostgreSQL.",
        reason="Required for JSONB and pgvector.",
    )
    add_decision(inp, project_path=target_dir)

    # Attempting to add an identical decision should raise ValueError
    with pytest.raises(ValueError, match="Duplicate decision"):
        add_decision(inp, project_path=target_dir)

    # CLI test for duplicate
    res = runner.invoke(
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
            "Required for JSONB and pgvector.",
            "-p",
            str(target_dir),
        ],
    )
    assert res.exit_code != 0
    assert "Duplicate decision" in res.output


def test_duplicate_note_rejected(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    inp = NoteInput(
        title="Local database",
        category="development",
        text="PostgreSQL runs through Docker Compose on port 5432.",
    )
    add_note(inp, project_path=target_dir)

    # Attempting to add an identical note should raise ValueError
    with pytest.raises(ValueError, match="Duplicate note"):
        add_note(inp, project_path=target_dir)

    # CLI test for duplicate
    res = runner.invoke(
        app,
        [
            "add",
            "note",
            "--title",
            "Local database",
            "--category",
            "development",
            "--text",
            "PostgreSQL runs through Docker Compose on port 5432.",
            "-p",
            str(target_dir),
        ],
    )
    assert res.exit_code != 0
    assert "Duplicate note" in res.output
