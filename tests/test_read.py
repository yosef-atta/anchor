import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anchor.cli import app
from anchor.core import (
    add_decision,
    add_note,
    get_record,
    initialize_project,
    sanitize_fts_query,
    search_records,
)
from anchor.models import DecisionInput, DecisionRecord, NoteInput, NoteRecord, Origin, RecordType

runner = CliRunner()


def test_get_decision_lookup(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="Primary database",
            category="database",
            decision="Use PostgreSQL.",
            reason="Required for JSONB and pgvector.",
            origin=Origin.LIVE,
        ),
        project_path=target_dir,
    )

    rec = get_record("D-000001", project_path=target_dir)
    assert rec is not None
    assert isinstance(rec, DecisionRecord)
    assert rec.id == "D-000001"
    assert rec.title == "Primary database"
    assert rec.category == "database"
    assert rec.decision == "Use PostgreSQL."
    assert rec.reason == "Required for JSONB and pgvector."
    assert rec.origin == Origin.LIVE


def test_get_note_lookup(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_note(
        NoteInput(
            title="Local port",
            category="development",
            text="Dev server runs on port 3000.",
            origin=Origin.BOOTSTRAP,
        ),
        project_path=target_dir,
    )

    rec = get_record("N-000001", project_path=target_dir)
    assert rec is not None
    assert isinstance(rec, NoteRecord)
    assert rec.id == "N-000001"
    assert rec.title == "Local port"
    assert rec.category == "development"
    assert rec.text == "Dev server runs on port 3000."
    assert rec.origin == Origin.BOOTSTRAP


def test_get_unknown_id(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    # Core lookup returns None
    assert get_record("D-999999", project_path=target_dir) is None
    assert get_record("N-999999", project_path=target_dir) is None
    assert get_record("UNKNOWN_ID", project_path=target_dir) is None

    # CLI returns exit code 1
    res = runner.invoke(app, ["get", "D-999999", "-p", str(target_dir)])
    assert res.exit_code != 0
    assert "not found" in res.output


def test_get_and_search_deleted_records(tmp_path: Path):
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

    # Default get excludes deleted
    assert get_record("D-000001", project_path=target_dir) is None
    assert get_record("N-000001", project_path=target_dir) is None

    # Explicit include_deleted=True returns them
    rec_d = get_record("D-000001", project_path=target_dir, include_deleted=True)
    assert rec_d is not None
    assert rec_d.deleted_at == "2026-09-08T00:00:00Z"

    rec_n = get_record("N-000001", project_path=target_dir, include_deleted=True)
    assert rec_n is not None
    assert rec_n.deleted_at == "2026-09-08T00:00:00Z"

    # Search excludes deleted by default
    search_res = search_records("Redis", project_path=target_dir)
    assert search_res.total == 0
    assert len(search_res.items) == 0

    # Search includes deleted when requested
    search_res_all = search_records("Redis", project_path=target_dir, include_deleted=True)
    assert search_res_all.total == 2
    assert len(search_res_all.items) == 2


def test_search_exact_and_partial_matches(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="Primary database engine",
            category="database",
            decision="Adopt PostgreSQL with pgvector extension.",
            reason="Required for embeddings and relational integrity.",
        ),
        project_path=target_dir,
    )
    add_note(
        NoteInput(
            title="Database migration runner",
            category="database",
            text="Run alembic upgrade head on deployment.",
        ),
        project_path=target_dir,
    )
    add_decision(
        DecisionInput(
            title="Frontend framework",
            category="frontend",
            decision="Use Next.js app router.",
            reason="SSR and React server components support.",
        ),
        project_path=target_dir,
    )

    # Exact search on title / category
    res = search_records("PostgreSQL", project_path=target_dir)
    assert res.total == 1
    assert res.items[0].id == "D-000001"
    assert res.items[0].record_type == RecordType.DECISION

    # Exact search across multiple fields (category & reason)
    res_db = search_records("database", project_path=target_dir)
    assert res_db.total == 2
    ids = {item.id for item in res_db.items}
    assert ids == {"D-000001", "N-000001"}

    # Partial / prefix search match (e.g. "migrat" matches "migration", "relat" matches "relational")
    res_partial = search_records("migrat", project_path=target_dir)
    assert res_partial.total == 1
    assert res_partial.items[0].id == "N-000001"

    res_vector = search_records("pgvect", project_path=target_dir)
    assert res_vector.total == 1
    assert res_vector.items[0].id == "D-000001"


def test_search_safe_handling_empty_and_malformed_queries(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="Auth cookies",
            category="auth",
            decision="Use HTTP-only secure cookies.",
            reason="Prevent XSS token theft.",
        ),
        project_path=target_dir,
    )

    # Empty & whitespace queries
    res_empty = search_records("", project_path=target_dir)
    assert res_empty.total == 0
    assert res_empty.items == []

    res_space = search_records("    ", project_path=target_dir)
    assert res_space.total == 0

    # Malformed queries with unbalanced quotes, syntax characters, colons, boolean operators
    malformed_queries = [
        '"""',
        "auth AND OR NOT (",
        "category:auth",
        'cookie" * ^',
        "(((((((",
        "::: ;;; !!! ???",
    ]
    for mq in malformed_queries:
        # Must not raise sqlite3.OperationalError or any uncaught exception
        res = search_records(mq, project_path=target_dir)
        assert isinstance(res.total, int)

    # Sanitize helper tests
    assert sanitize_fts_query("") == ""
    assert sanitize_fts_query("   ") == ""
    assert sanitize_fts_query("!@#$%^&*()") == ""
    assert '"auth"*' in sanitize_fts_query("auth")


def test_search_pagination_and_deterministic_ordering(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    # Create 25 records matching the term "item"
    for i in range(1, 26):
        add_note(
            NoteInput(
                title=f"Configuration item {i:02d}",
                category="config",
                text=f"Configuration note body item {i:02d}.",
            ),
            project_path=target_dir,
        )

    # Page 1 (default page_size=20)
    res_p1 = search_records("item", project_path=target_dir, page=1, page_size=20)
    assert res_p1.total == 25
    assert len(res_p1.items) == 20
    assert res_p1.page == 1
    assert res_p1.page_size == 20

    # Page 2
    res_p2 = search_records("item", project_path=target_dir, page=2, page_size=20)
    assert res_p2.total == 25
    assert len(res_p2.items) == 5
    assert res_p2.page == 2

    # Deterministic ordering check: running the query twice yields the exact same list
    res_p1_repeat = search_records("item", project_path=target_dir, page=1, page_size=20)
    assert [item.id for item in res_p1.items] == [item.id for item in res_p1_repeat.items]

    # Check that items in page 1 and page 2 do not overlap
    p1_ids = {item.id for item in res_p1.items}
    p2_ids = {item.id for item in res_p2.items}
    assert p1_ids.isdisjoint(p2_ids)
    assert len(p1_ids | p2_ids) == 25


def test_cli_get_and_search(tmp_path: Path):
    target_dir = tmp_path / "proj"
    runner.invoke(app, ["init", str(target_dir)])

    # Add a decision and a note
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
            "Dev port",
            "--category",
            "dev",
            "--text",
            "Port 3000",
            "-p",
            str(target_dir),
        ],
    )

    # CLI get decision
    get_d = runner.invoke(app, ["get", "D-000001", "-p", str(target_dir)])
    assert get_d.exit_code == 0
    assert "D-000001" in get_d.output
    assert "Primary database" in get_d.output
    assert "Use PostgreSQL." in get_d.output

    # CLI get note
    get_n = runner.invoke(app, ["get", "N-000001", "-p", str(target_dir)])
    assert get_n.exit_code == 0
    assert "N-000001" in get_n.output
    assert "Dev port" in get_n.output
    assert "Port 3000" in get_n.output

    # CLI get unknown ID
    get_unknown = runner.invoke(app, ["get", "D-999999", "-p", str(target_dir)])
    assert get_unknown.exit_code != 0
    assert "Record 'D-999999' not found" in get_unknown.output

    # CLI search match
    search_match = runner.invoke(app, ["search", "database", "-p", str(target_dir)])
    assert search_match.exit_code == 0
    assert "D-000001" in search_match.output
    assert "Primary database" in search_match.output

    # CLI search no match
    search_no_match = runner.invoke(app, ["search", "nonexistentterm", "-p", str(target_dir)])
    assert search_no_match.exit_code == 0
    assert "No results found" in search_no_match.output

    # CLI search with pagination arguments
    search_page = runner.invoke(app, ["search", "database", "--page", "1", "--page-size", "10", "-p", str(target_dir)])
    assert search_page.exit_code == 0
    assert "Page 1 of 1" in search_page.output


def test_uninitialized_project_get_and_search_fails(tmp_path: Path):
    uninit_dir = tmp_path / "uninit"
    uninit_dir.mkdir()

    with pytest.raises(ValueError, match="not initialized"):
        get_record("D-000001", project_path=uninit_dir)

    with pytest.raises(ValueError, match="not initialized"):
        search_records("test", project_path=uninit_dir)

    res_get = runner.invoke(app, ["get", "D-000001", "-p", str(uninit_dir)])
    assert res_get.exit_code != 0

    res_search = runner.invoke(app, ["search", "test", "-p", str(uninit_dir)])
    assert res_search.exit_code != 0
