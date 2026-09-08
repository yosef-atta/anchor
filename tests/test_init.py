import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from anchor.cli import app

runner = CliRunner()


def test_init_command_creates_files(tmp_path: Path):
    target_dir = tmp_path / "my_project"
    target_dir.mkdir()
    
    result = runner.invoke(app, ["init", str(target_dir)])
    assert result.exit_code == 0
    assert "Initialized Anchor" in result.output
    assert '"mcpServers"' in result.output
    assert '"anchor"' in result.output
    
    # Check directory and files
    assert (target_dir / ".anchor" / "anchor.db").exists()
    assert (target_dir / ".anchor" / ".gitignore").exists()
    assert (target_dir / ".anchor" / ".gitignore").read_text(encoding="utf-8").strip() == "*"
    agents_content = (target_dir / "AGENTS.md").read_text(encoding="utf-8")
    claude_content = (target_dir / "CLAUDE.md").read_text(encoding="utf-8")
    
    assert "<!-- anchor:start -->" in agents_content
    assert "<!-- anchor:end -->" in agents_content
    assert agents_content == claude_content
    
    # Check database
    db_path = target_dir / ".anchor" / "anchor.db"
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'version'")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "1"


def test_init_preserves_custom_content(tmp_path: Path):
    target_dir = tmp_path / "custom_proj"
    target_dir.mkdir()
    
    (target_dir / "AGENTS.md").write_text("# My Custom Header\nSome other instructions\n", encoding="utf-8")
    result = runner.invoke(app, ["init", str(target_dir)])
    assert result.exit_code == 0
    
    content = (target_dir / "AGENTS.md").read_text(encoding="utf-8")
    assert "# My Custom Header" in content
    assert "<!-- anchor:start -->" in content
    assert "<!-- anchor:end -->" in content
