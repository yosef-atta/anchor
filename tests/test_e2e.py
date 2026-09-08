import json
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from typer.testing import CliRunner

from anchor import __version__
from anchor.cli import app

runner = CliRunner()


def test_cli_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"anchor version {__version__}" in result.stdout

    # Subprocess execution test
    proc = subprocess.run([sys.executable, "-m", "anchor.cli", "--version"], capture_output=True, text=True)
    assert proc.returncode == 0
    assert f"anchor version {__version__}" in proc.stdout


def test_e2e_cli_poc_workflow_new_project(tmp_path: Path):
    project_dir = tmp_path / "new_project"
    project_dir.mkdir()

    # 1. anchor init
    res_init = runner.invoke(app, ["init", str(project_dir)])
    assert res_init.exit_code == 0
    assert "Initialized Anchor" in res_init.stdout
    assert (project_dir / ".anchor" / "anchor.db").exists()
    assert (project_dir / "AGENTS.md").exists()
    assert (project_dir / "CLAUDE.md").exists()

    # 2. anchor status
    res_status = runner.invoke(app, ["status", str(project_dir)])
    assert res_status.exit_code == 0
    assert "project_type: new" in res_status.stdout
    assert "decisions: 0" in res_status.stdout
    assert "notes: 0" in res_status.stdout

    # 3. anchor add decision
    res_add_d = runner.invoke(
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
            str(project_dir),
        ],
    )
    assert res_add_d.exit_code == 0
    assert "D-000001" in res_add_d.stdout

    # 4. anchor add note
    res_add_n = runner.invoke(
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
            str(project_dir),
        ],
    )
    assert res_add_n.exit_code == 0
    assert "N-000001" in res_add_n.stdout

    # 5. anchor get
    res_get_d = runner.invoke(app, ["get", "D-000001", "-p", str(project_dir)])
    assert res_get_d.exit_code == 0
    assert "Primary database" in res_get_d.stdout
    assert "Use PostgreSQL." in res_get_d.stdout

    # 6. anchor search
    res_search = runner.invoke(app, ["search", "PostgreSQL", "-p", str(project_dir)])
    assert res_search.exit_code == 0
    assert "D-000001" in res_search.stdout
    assert "N-000001" in res_search.stdout

    # 7. anchor context
    res_ctx = runner.invoke(app, ["context", "replace PostgreSQL with MySQL", "-p", str(project_dir), "--json"])
    assert res_ctx.exit_code == 0
    ctx_data = json.loads(res_ctx.stdout)
    assert len(ctx_data["decisions"]) == 1
    assert ctx_data["decisions"][0]["id"] == "D-000001"

    # 8. anchor edit
    res_edit = runner.invoke(
        app,
        [
            "edit",
            "D-000001",
            "--decision",
            "Use MySQL.",
            "--reason",
            "Production infrastructure requires MySQL.",
            "-p",
            str(project_dir),
        ],
    )
    assert res_edit.exit_code == 0
    assert "Updated record D-000001" in res_edit.stdout

    # 9. anchor apply batch
    batch_file = project_dir / "batch.json"
    batch_file.write_text(
        json.dumps(
            {
                "operations": [
                    {
                        "action": "edit",
                        "id": "N-000001",
                        "changes": {"text": "MySQL runs through Docker Compose on port 3306."},
                    },
                    {
                        "action": "add_decision",
                        "data": {
                            "title": "ORM framework",
                            "category": "database",
                            "decision": "Use SQLAlchemy 2.0.",
                            "reason": "Standard typed ORM in Python.",
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    res_apply = runner.invoke(app, ["apply", str(batch_file), "-p", str(project_dir)])
    assert res_apply.exit_code == 0
    assert "Successfully applied 2 batch operations" in res_apply.stdout

    # 10. verify updated context
    res_ctx2 = runner.invoke(app, ["context", "database connection", "-p", str(project_dir), "--json"])
    assert res_ctx2.exit_code == 0
    ctx2_data = json.loads(res_ctx2.stdout)
    d_ids = [d["id"] for d in ctx2_data["decisions"]]
    assert "D-000001" in d_ids
    assert "D-000002" in d_ids


@pytest.mark.asyncio
async def test_e2e_mcp_poc_workflow_stdio(tmp_path: Path):
    project_dir = tmp_path / "mcp_project"
    project_dir.mkdir()
    (project_dir / "setup.py").write_text("from setuptools import setup", encoding="utf-8")

    # Initialize project first
    from anchor.core import initialize_project

    init_res = initialize_project(project_dir)
    assert init_res["is_existing"] is True

    # Connect MCP client over STDIO to `anchor mcp`
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "anchor.cli", "mcp"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. anchor_status
            status_res = await session.call_tool("anchor_status", {"path": str(project_dir)})
            assert status_res.structured_content is not None
            assert status_res.structured_content["initialized"] is True
            assert status_res.structured_content["project_type"] == "existing"
            assert status_res.structured_content["bootstrap_status"] == "pending"

            # 2. bootstrap memory writes: anchor_add_decision & anchor_add_note
            add_d_res = await session.call_tool(
                "anchor_add_decision",
                {
                    "title": "Build System",
                    "category": "tooling",
                    "decision": "Use setuptools and pip.",
                    "reason": "Existing setup.py observed in repo.",
                    "origin": "bootstrap",
                    "path": str(project_dir),
                },
            )
            assert add_d_res.structured_content is not None
            assert add_d_res.structured_content["id"] == "D-000001"
            assert add_d_res.structured_content["origin"] == "bootstrap"

            add_n_res = await session.call_tool(
                "anchor_add_note",
                {
                    "title": "Legacy dependency",
                    "category": "dependencies",
                    "text": "Requires Python 3.10+ compatibility.",
                    "origin": "bootstrap",
                    "path": str(project_dir),
                },
            )
            assert add_n_res.structured_content is not None
            assert add_n_res.structured_content["id"] == "N-000001"

            # 3. anchor_complete_bootstrap
            comp_res = await session.call_tool("anchor_complete_bootstrap", {"path": str(project_dir)})
            assert comp_res.structured_content is not None
            assert comp_res.structured_content["bootstrap_status"] == "complete"

            # 4. anchor_status after completion
            status2_res = await session.call_tool("anchor_status", {"path": str(project_dir)})
            assert status2_res.structured_content is not None
            assert status2_res.structured_content["bootstrap_status"] == "complete"
            assert status2_res.structured_content["decisions"] == 1
            assert status2_res.structured_content["notes"] == 1

            # 5. retrieve context: anchor_context
            ctx_res = await session.call_tool(
                "anchor_context",
                {"query": "modernize build system", "path": str(project_dir)},
            )
            assert ctx_res.structured_content is not None
            assert len(ctx_res.structured_content["decisions"]) == 1

            # 6. mutate decision: anchor_edit
            edit_res = await session.call_tool(
                "anchor_edit",
                {
                    "id": "D-000001",
                    "decision": "Migrate from setuptools to uv/hatchling.",
                    "reason": "Fast builds and modern packaging.",
                    "origin": "live",
                    "path": str(project_dir),
                },
            )
            assert edit_res.structured_content is not None
            assert edit_res.structured_content["decision"] == "Migrate from setuptools to uv/hatchling."
            assert edit_res.structured_content["origin"] == "live"

            # 7. atomic batch: anchor_apply_batch
            batch_res = await session.call_tool(
                "anchor_apply_batch",
                {
                    "operations": [
                        {
                            "action": "delete",
                            "id": "N-000001",
                        },
                        {
                            "action": "add_note",
                            "data": {
                                "title": "Packaging manager",
                                "category": "tooling",
                                "text": "Use uv for dependency resolution.",
                            },
                        },
                    ],
                    "path": str(project_dir),
                },
            )
            assert batch_res.structured_content is not None
            assert batch_res.structured_content["applied"] == 2

            # 8. anchor_get verification
            get_d = await session.call_tool("anchor_get", {"id": "D-000001", "path": str(project_dir)})
            assert get_d.structured_content is not None
            assert get_d.structured_content["title"] == "Build System"
