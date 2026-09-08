import pytest
from mcp.types import CallToolResult
from typer.testing import CliRunner

from anchor.cli import app
from anchor.core import complete_bootstrap, get_project_status, initialize_project
from anchor.mcp_server import create_mcp_server

runner = CliRunner()


def test_existing_project_pending_bootstrap_state(tmp_path):
    # Create an existing non-anchor file to trigger existing project detection
    (tmp_path / "package.json").write_text('{"name": "test-repo"}', encoding="utf-8")

    init_res = initialize_project(tmp_path)
    assert init_res["is_existing"] is True

    status = get_project_status(tmp_path)
    assert status["initialized"] is True
    assert status["project_type"] == "existing"
    assert status["bootstrap_status"] == "pending"


def test_bootstrap_origin_records_and_completion_lifecycle(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.js").write_text("console.log('hello');", encoding="utf-8")

    initialize_project(tmp_path)

    # Add bootstrap decision
    res_dec = runner.invoke(
        app,
        [
            "add",
            "decision",
            "--title",
            "Observed Architecture",
            "--category",
            "architecture",
            "--decision",
            "Node.js ES Modules",
            "--reason",
            "Found package.json with type module",
            "--origin",
            "bootstrap",
            "-p",
            str(tmp_path),
        ],
    )
    assert res_dec.exit_code == 0
    assert "bootstrap" in res_dec.stdout

    # Add bootstrap note
    res_note = runner.invoke(
        app,
        [
            "add",
            "note",
            "--title",
            "Build script",
            "--category",
            "tooling",
            "--text",
            "Uses npm run build",
            "--origin",
            "bootstrap",
            "-p",
            str(tmp_path),
        ],
    )
    assert res_note.exit_code == 0

    # Check status before complete
    status_before = get_project_status(tmp_path)
    assert status_before["bootstrap_status"] == "pending"
    assert status_before["decisions"] == 1
    assert status_before["notes"] == 1

    # Transition completion via CLI
    comp_res = runner.invoke(app, ["bootstrap", "complete", str(tmp_path)])
    assert comp_res.exit_code == 0
    assert "complete" in comp_res.stdout

    # Verify status after completion
    status_after = get_project_status(tmp_path)
    assert status_after["bootstrap_status"] == "complete"

    # Idempotent completion check: running complete again succeeds
    comp_res_2 = runner.invoke(app, ["bootstrap", "complete", str(tmp_path)])
    assert comp_res_2.exit_code == 0
    status_after_2 = get_project_status(tmp_path)
    assert status_after_2["bootstrap_status"] == "complete"


def test_core_complete_bootstrap_idempotence(tmp_path):
    (tmp_path / "main.py").write_text("print('test')", encoding="utf-8")
    initialize_project(tmp_path)

    res1 = complete_bootstrap(tmp_path)
    assert res1["bootstrap_status"] == "complete"
    first_completed_at = res1["bootstrap_completed_at"]

    res2 = complete_bootstrap(tmp_path)
    assert res2["bootstrap_status"] == "complete"
    assert res2["bootstrap_completed_at"] == first_completed_at


@pytest.mark.asyncio
async def test_mcp_complete_bootstrap(tmp_path):
    (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'", encoding="utf-8")
    initialize_project(tmp_path)

    mcp_server = create_mcp_server()
    res = await mcp_server.call_tool("anchor_complete_bootstrap", {"path": str(tmp_path)})
    assert isinstance(res, CallToolResult)
    assert res.structured_content is not None
    assert res.structured_content["bootstrap_status"] == "complete"
