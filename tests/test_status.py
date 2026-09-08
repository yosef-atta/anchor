import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from anchor.cli import app
from anchor.core import initialize_project

runner = CliRunner()


def test_status_uninitialized(tmp_path: Path):
    target_dir = tmp_path / "empty_proj"
    target_dir.mkdir()
    
    result = runner.invoke(app, ["status", str(target_dir)])
    assert result.exit_code == 0
    assert "initialized: false" in result.output
    assert str(target_dir.resolve()) in result.output


def test_status_initialized_new(tmp_path: Path):
    target_dir = tmp_path / "new_proj"
    target_dir.mkdir()
    
    initialize_project(target_dir)
    
    result = runner.invoke(app, ["status", str(target_dir)])
    assert result.exit_code == 0
    assert "initialized: true" in result.output
    assert "project_type: new" in result.output
    assert "bootstrap_status: none" in result.output
    assert "decisions: 0" in result.output
    assert "notes: 0" in result.output


def test_status_initialized_existing_with_records(tmp_path: Path):
    target_dir = tmp_path / "existing_proj"
    target_dir.mkdir()
    (target_dir / "package.json").write_text("{}", encoding="utf-8")
    
    initialize_project(target_dir)
    
    db_path = target_dir / ".anchor" / "anchor.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO decisions (id, seq, title, category, decision, reason, origin, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("D-000001", 1, "DB Choice", "database", "Use SQLite", "Simple", "live", "2026-01-01", "2026-01-01")
        )
        cursor.execute(
            "INSERT INTO notes (id, seq, title, category, text, origin, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("N-000001", 1, "Dev Note", "dev", "Dev note content", "live", "2026-01-01", "2026-01-01")
        )
        conn.commit()
        
    result = runner.invoke(app, ["status", str(target_dir)])
    assert result.exit_code == 0
    assert "initialized: true" in result.output
    assert "project_type: existing" in result.output
    assert "bootstrap_status: pending" in result.output
    assert "decisions: 1" in result.output
    assert "notes: 1" in result.output
