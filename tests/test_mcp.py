import pytest
from mcp.server.mcpserver.exceptions import ToolError

from anchor.core import initialize_project
from anchor.mcp_server import create_mcp_server


@pytest.fixture
def mcp_server():
    return create_mcp_server()


@pytest.fixture
def project_dir(tmp_path):
    initialize_project(tmp_path)
    return tmp_path


@pytest.mark.asyncio
async def test_mcp_tool_registration(mcp_server):
    tools = await mcp_server.list_tools()
    tool_names = {t.name for t in tools}
    expected_tools = {
        "anchor_status",
        "anchor_search",
        "anchor_context",
        "anchor_get",
        "anchor_add_decision",
        "anchor_add_note",
        "anchor_edit",
        "anchor_delete",
        "anchor_apply_batch",
        "anchor_complete_bootstrap",
    }
    assert expected_tools.issubset(tool_names)


@pytest.mark.asyncio
async def test_mcp_status_tool(mcp_server, project_dir):
    res = await mcp_server.call_tool("anchor_status", {"path": str(project_dir)})
    assert res.structured_content is not None
    data = res.structured_content
    assert data["initialized"] is True
    assert data["decisions"] == 0
    assert data["notes"] == 0


@pytest.mark.asyncio
async def test_mcp_add_and_get_decision(mcp_server, project_dir):
    # Add decision
    add_res = await mcp_server.call_tool(
        "anchor_add_decision",
        {
            "title": "Database choice",
            "category": "database",
            "decision": "Use PostgreSQL.",
            "reason": "Needs JSONB support.",
            "origin": "live",
            "path": str(project_dir),
        },
    )
    assert add_res.structured_content is not None
    dec = add_res.structured_content
    assert dec["id"] == "D-000001"
    assert dec["title"] == "Database choice"
    assert dec["decision"] == "Use PostgreSQL."

    # Get decision
    get_res = await mcp_server.call_tool(
        "anchor_get",
        {
            "id": "D-000001",
            "path": str(project_dir),
        },
    )
    assert get_res.structured_content is not None
    rec = get_res.structured_content
    assert rec["id"] == "D-000001"
    assert rec["title"] == "Database choice"


@pytest.mark.asyncio
async def test_mcp_add_and_get_note(mcp_server, project_dir):
    add_res = await mcp_server.call_tool(
        "anchor_add_note",
        {
            "title": "Local Port",
            "category": "network",
            "text": "Server runs on port 8080.",
            "origin": "bootstrap",
            "path": str(project_dir),
        },
    )
    assert add_res.structured_content is not None
    note = add_res.structured_content
    assert note["id"] == "N-000001"
    assert note["text"] == "Server runs on port 8080."
    assert note["origin"] == "bootstrap"

    get_res = await mcp_server.call_tool(
        "anchor_get",
        {
            "id": "N-000001",
            "path": str(project_dir),
        },
    )
    assert get_res.structured_content is not None
    assert get_res.structured_content["id"] == "N-000001"


@pytest.mark.asyncio
async def test_mcp_search_and_context(mcp_server, project_dir):
    await mcp_server.call_tool(
        "anchor_add_decision",
        {
            "title": "Authentication method",
            "category": "auth",
            "decision": "Use session cookies with JWT.",
            "reason": "Simplicity and security.",
            "path": str(project_dir),
        },
    )
    await mcp_server.call_tool(
        "anchor_add_note",
        {
            "title": "Auth secret",
            "category": "auth",
            "text": "Set JWT_SECRET in environment.",
            "path": str(project_dir),
        },
    )

    # Search
    search_res = await mcp_server.call_tool(
        "anchor_search",
        {
            "query": "session JWT",
            "path": str(project_dir),
        },
    )
    assert search_res.structured_content is not None
    search_data = search_res.structured_content
    assert search_data["total"] >= 1
    assert len(search_data["items"]) >= 1

    # Context
    ctx_res = await mcp_server.call_tool(
        "anchor_context",
        {
            "query": "implement session authentication",
            "path": str(project_dir),
        },
    )
    assert ctx_res.structured_content is not None
    ctx_data = ctx_res.structured_content
    assert len(ctx_data["decisions"]) == 1
    assert ctx_data["decisions"][0]["id"] == "D-000001"


@pytest.mark.asyncio
async def test_mcp_edit_and_delete(mcp_server, project_dir):
    await mcp_server.call_tool(
        "anchor_add_decision",
        {
            "title": "Cache store",
            "category": "cache",
            "decision": "Use Redis.",
            "reason": "Fast in-memory cache.",
            "path": str(project_dir),
        },
    )

    # Edit
    edit_res = await mcp_server.call_tool(
        "anchor_edit",
        {
            "id": "D-000001",
            "decision": "Use DragonFly BSD or Redis.",
            "path": str(project_dir),
        },
    )
    assert edit_res.structured_content is not None
    assert edit_res.structured_content["decision"] == "Use DragonFly BSD or Redis."

    # Delete
    del_res = await mcp_server.call_tool(
        "anchor_delete",
        {
            "id": "D-000001",
            "path": str(project_dir),
        },
    )
    assert del_res.structured_content is not None
    assert del_res.structured_content["deleted_at"] is not None

    # Get non-existent / deleted
    with pytest.raises(ToolError, match="not found"):
        await mcp_server.call_tool(
            "anchor_get",
            {
                "id": "D-000001",
                "path": str(project_dir),
            },
        )


@pytest.mark.asyncio
async def test_mcp_apply_batch(mcp_server, project_dir):
    ops = [
        {
            "action": "add_decision",
            "data": {
                "title": "Storage provider",
                "category": "storage",
                "decision": "Use AWS S3.",
                "reason": "Scalable blob storage.",
            },
        },
        {
            "action": "add_note",
            "data": {
                "title": "S3 bucket name",
                "category": "storage",
                "text": "Bucket name is app-assets-prod.",
            },
        },
    ]

    batch_res = await mcp_server.call_tool(
        "anchor_apply_batch",
        {
            "operations": ops,
            "path": str(project_dir),
        },
    )
    assert batch_res.structured_content is not None
    assert batch_res.structured_content["applied"] == 2
    assert len(batch_res.structured_content["records"]) == 2


@pytest.mark.asyncio
async def test_mcp_error_handling(mcp_server, project_dir, tmp_path_factory):
    # Unknown record get
    with pytest.raises(ToolError, match="Record 'D-999999' not found"):
        await mcp_server.call_tool("anchor_get", {"id": "D-999999", "path": str(project_dir)})

    # Uninitialized project path on write raises ToolError
    uninit_dir = tmp_path_factory.mktemp("completely_uninit")
    with pytest.raises(ToolError, match="not initialized"):
        await mcp_server.call_tool(
            "anchor_add_decision",
            {
                "title": "T",
                "category": "C",
                "decision": "D",
                "reason": "R",
                "path": str(uninit_dir),
            },
        )

    # Status on uninitialized path returns initialized: False
    status_res = await mcp_server.call_tool("anchor_status", {"path": str(uninit_dir)})
    assert status_res.structured_content is not None
    assert status_res.structured_content["initialized"] is False
