import json
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from anchor.cli import app
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
from anchor.models import (
    DecisionInput,
    DecisionRecord,
    NoteInput,
    NoteRecord,
)

runner = CliRunner()


def test_partial_edit_decision(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    d = add_decision(
        DecisionInput(
            title="Primary DB",
            category="database",
            decision="Use PostgreSQL.",
            reason="Relational support.",
        ),
        project_path=target_dir,
    )
    time.sleep(0.01)

    updated = edit_record(
        d.id,
        {"decision": "Use MySQL.", "reason": "Production requires MySQL."},
        project_path=target_dir,
    )

    assert isinstance(updated, DecisionRecord)
    assert updated.id == d.id
    assert updated.title == "Primary DB"
    assert updated.category == "database"
    assert updated.decision == "Use MySQL."
    assert updated.reason == "Production requires MySQL."
    assert updated.updated_at > d.created_at
    assert updated.deleted_at is None

    # Fetch from DB and check
    fetched = get_record(d.id, project_path=target_dir)
    assert isinstance(fetched, DecisionRecord)
    assert fetched.decision == "Use MySQL."


def test_partial_edit_note(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    n = add_note(
        NoteInput(
            title="Dev port",
            category="dev",
            text="Port 3000",
        ),
        project_path=target_dir,
    )
    time.sleep(0.01)

    updated = edit_record(
        n.id,
        {"text": "Port 8080", "category": "infrastructure"},
        project_path=target_dir,
    )

    assert isinstance(updated, NoteRecord)
    assert updated.id == n.id
    assert updated.title == "Dev port"
    assert updated.category == "infrastructure"
    assert updated.text == "Port 8080"
    assert updated.updated_at > n.created_at


def test_invalid_edits_rejected(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    d = add_decision(
        DecisionInput(
            title="DB Choice",
            category="db",
            decision="Postgres",
            reason="Features",
        ),
        project_path=target_dir,
    )

    n = add_note(
        NoteInput(
            title="Cache Port",
            category="cache",
            text="6379",
        ),
        project_path=target_dir,
    )

    # Note field applied to decision
    with pytest.raises(ValueError, match="Cannot apply note field 'text'"):
        edit_record(d.id, {"text": "invalid"}, project_path=target_dir)

    # Decision field applied to note
    with pytest.raises(ValueError, match="Cannot apply decision field"):
        edit_record(n.id, {"decision": "invalid"}, project_path=target_dir)

    with pytest.raises(ValueError, match="Cannot apply decision field"):
        edit_record(n.id, {"reason": "invalid"}, project_path=target_dir)

    # Empty string update
    with pytest.raises(ValueError, match="must be a non-empty string"):
        edit_record(d.id, {"title": "   "}, project_path=target_dir)

    # Empty changes dictionary
    with pytest.raises(ValueError, match="No changes provided"):
        edit_record(d.id, {}, project_path=target_dir)

    # Unknown field
    with pytest.raises(ValueError, match="Invalid field"):
        edit_record(d.id, {"non_existent_field": "val"}, project_path=target_dir)

    # Non-existent ID
    with pytest.raises(ValueError, match="Record 'D-999999' not found"):
        edit_record("D-999999", {"title": "New"}, project_path=target_dir)


def test_duplicate_on_edit_rejected(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    add_decision(
        DecisionInput(
            title="DB 1",
            category="db",
            decision="Postgres",
            reason="Features",
        ),
        project_path=target_dir,
    )
    d2 = add_decision(
        DecisionInput(
            title="DB 2",
            category="db",
            decision="MySQL",
            reason="Legacy",
        ),
        project_path=target_dir,
    )

    # Updating d2 to have identical content to d1 must fail
    with pytest.raises(ValueError, match="Duplicate decision"):
        edit_record(
            d2.id,
            {"title": "DB 1", "decision": "Postgres", "reason": "Features"},
            project_path=target_dir,
        )


def test_soft_deletion_lifecycle(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    d = add_decision(
        DecisionInput(
            title="Temp DB",
            category="db",
            decision="SQLite",
            reason="Simple",
        ),
        project_path=target_dir,
    )

    del_record = delete_record(d.id, project_path=target_dir)
    assert del_record.id == d.id
    assert del_record.deleted_at is not None

    # Status reflects deleted
    status = get_project_status(project_path=target_dir)
    assert status["decisions"] == 0

    # get_record by default returns None
    assert get_record(d.id, project_path=target_dir) is None
    # get_record with include_deleted=True returns it
    assert get_record(d.id, project_path=target_dir, include_deleted=True) is not None

    # Second delete fails
    with pytest.raises(ValueError, match="already deleted"):
        delete_record(d.id, project_path=target_dir)

    # Editing a deleted record fails
    with pytest.raises(ValueError, match="Cannot edit deleted record"):
        edit_record(d.id, {"title": "Revived"}, project_path=target_dir)


def test_fts_synchronization_after_edit_and_delete(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    d = add_decision(
        DecisionInput(
            title="SearchEngine Choice",
            category="search",
            decision="Use Meilisearch for ultra-fast indexing.",
            reason="Superior typo tolerance.",
        ),
        project_path=target_dir,
    )

    # Initial search
    res1 = search_records("Meilisearch", project_path=target_dir)
    assert res1.total == 1
    assert res1.items[0].id == d.id

    # Edit decision: replace Meilisearch with Elasticsearch
    edit_record(
        d.id,
        {"decision": "Use Elasticsearch for cluster scale."},
        project_path=target_dir,
    )

    # Old term should no longer match
    res_old = search_records("Meilisearch", project_path=target_dir)
    assert res_old.total == 0

    # New term matches
    res_new = search_records("Elasticsearch", project_path=target_dir)
    assert res_new.total == 1
    assert res_new.items[0].id == d.id

    # Context query reflects new content
    ctx = get_context("Elasticsearch", project_path=target_dir)
    assert len(ctx.decisions) == 1
    assert "Elasticsearch" in ctx.decisions[0].decision

    # Soft delete
    delete_record(d.id, project_path=target_dir)

    # Search excluded by default
    res_deleted = search_records("Elasticsearch", project_path=target_dir)
    assert res_deleted.total == 0

    # Search with include_deleted=True finds it
    res_del_inc = search_records("Elasticsearch", project_path=target_dir, include_deleted=True)
    assert res_del_inc.total == 1

    # Context search excludes deleted by default
    ctx_del = get_context("Elasticsearch", project_path=target_dir)
    assert len(ctx_del.decisions) == 0


def test_batch_mutation_success(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    d1 = add_decision(
        DecisionInput(
            title="Database",
            category="db",
            decision="Postgres",
            reason="JSONB",
        ),
        project_path=target_dir,
    )
    n1 = add_note(
        NoteInput(
            title="Dev note",
            category="dev",
            text="Initial note",
        ),
        project_path=target_dir,
    )

    mutation_dict = {
        "operations": [
            {
                "action": "edit",
                "id": d1.id,
                "changes": {
                    "decision": "Use MariaDB.",
                    "reason": "Enterprise licensing.",
                },
            },
            {
                "action": "delete",
                "id": n1.id,
            },
            {
                "action": "add_decision",
                "data": {
                    "title": "Auth scheme",
                    "category": "auth",
                    "decision": "JWT cookies",
                    "reason": "Stateless",
                },
            },
            {
                "action": "add_note",
                "data": {
                    "title": "Redis Cache",
                    "category": "infra",
                    "text": "Redis on 6379",
                },
            },
        ]
    }

    batch_file = target_dir / "mutation.json"
    batch_file.write_text(json.dumps(mutation_dict), encoding="utf-8")

    res = apply_batch(batch_file, project_path=target_dir)
    assert res.applied == 4
    assert len(res.records) == 4

    # Check state
    status = get_project_status(project_path=target_dir)
    assert status["decisions"] == 2  # d1 updated, new decision added
    assert status["notes"] == 1      # n1 deleted, new note added

    # Check d1 updated
    d1_check = get_record(d1.id, project_path=target_dir)
    assert isinstance(d1_check, DecisionRecord)
    assert d1_check.decision == "Use MariaDB."

    # Check n1 deleted
    assert get_record(n1.id, project_path=target_dir) is None


def test_batch_mutation_atomic_rollback(tmp_path: Path):
    target_dir = tmp_path / "proj"
    initialize_project(target_dir)

    d1 = add_decision(
        DecisionInput(
            title="Database",
            category="db",
            decision="Postgres",
            reason="JSONB",
        ),
        project_path=target_dir,
    )

    mutation_dict = {
        "operations": [
            {
                "action": "edit",
                "id": d1.id,
                "changes": {
                    "decision": "Use Cassandra.",
                },
            },
            {
                "action": "add_decision",
                "data": {
                    "title": "Valid New Decision",
                    "category": "arch",
                    "decision": "Microservices",
                    "reason": "Decoupled",
                },
            },
            {
                # Failing operation: non-existent record
                "action": "edit",
                "id": "D-999999",
                "changes": {
                    "title": "Does not exist",
                },
            },
        ]
    }

    batch_file = target_dir / "failed_mutation.json"
    batch_file.write_text(json.dumps(mutation_dict), encoding="utf-8")

    with pytest.raises(ValueError, match="Record 'D-999999' not found"):
        apply_batch(batch_file, project_path=target_dir)

    # Verify rollback: d1 must NOT have changed to Cassandra
    d1_check = get_record(d1.id, project_path=target_dir)
    assert isinstance(d1_check, DecisionRecord)
    assert d1_check.decision == "Postgres"

    # Verify rollback: "Valid New Decision" must NOT exist in the database
    res = search_records("Microservices", project_path=target_dir)
    assert res.total == 0

    status = get_project_status(project_path=target_dir)
    assert status["decisions"] == 1


def test_cli_edit_delete_apply(tmp_path: Path):
    target_dir = tmp_path / "proj"
    runner.invoke(app, ["init", str(target_dir)])

    # Add a decision via CLI
    runner.invoke(
        app,
        [
            "add",
            "decision",
            "--title", "Auth method",
            "--category", "auth",
            "--decision", "Sessions",
            "--reason", "Simplicity",
            "-p", str(target_dir),
        ],
    )

    # Edit via CLI
    edit_res = runner.invoke(
        app,
        [
            "edit",
            "D-000001",
            "--decision", "OAuth2 with PKCE",
            "--reason", "Security standard",
            "-p", str(target_dir),
        ],
    )
    assert edit_res.exit_code == 0
    assert "Updated record D-000001: Auth method" in edit_res.output

    # Get to verify CLI edit
    get_res = runner.invoke(app, ["get", "D-000001", "-p", str(target_dir)])
    assert "OAuth2 with PKCE" in get_res.output

    # Edit with no fields provided fails
    empty_edit = runner.invoke(app, ["edit", "D-000001", "-p", str(target_dir)])
    assert empty_edit.exit_code != 0
    assert "No fields provided to edit" in empty_edit.output

    # Delete via CLI
    del_res = runner.invoke(app, ["delete", "D-000001", "-p", str(target_dir)])
    assert del_res.exit_code == 0
    assert "Soft-deleted decision D-000001: Auth method" in del_res.output

    # Apply batch via CLI
    mutation = {
        "operations": [
            {
                "action": "add_note",
                "data": {
                    "title": "Batch Note",
                    "category": "cli",
                    "text": "Created via batch apply",
                },
            }
        ]
    }
    batch_file = target_dir / "cli_batch.json"
    batch_file.write_text(json.dumps(mutation), encoding="utf-8")

    apply_res = runner.invoke(app, ["apply", str(batch_file), "-p", str(target_dir)])
    assert apply_res.exit_code == 0
    assert "Successfully applied 1 batch operations" in apply_res.output
