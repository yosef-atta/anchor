# ⚓ Anchor

> **Local project-memory and decision system for agentic software development.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Standard%20STDIO-green.svg)](https://modelcontextprotocol.io/)
[![SQLite](https://img.shields.io/badge/storage-SQLite%20FTS5-orange.svg)](https://www.sqlite.org/)
[![Status](https://img.shields.io/badge/status-Proof%20of%20Concept%20(POC)-yellow.svg)](#-current-status-proof-of-concept-poc)

---

## 📌 Current Status: Proof of Concept (POC)

Anchor is currently in **Proof of Concept (POC)** stage. All core memory lifecycles, SQLite FTS5 search engines, CLI commands, and MCP tools are fully implemented, tested, and ready for local use with AI coding agents.

---

## 💡 Why Anchor?

In agentic software development, AI coding agents frequently suffer from **context drift** and **documentation bloat**:
- Project decisions get scattered across `PRD.md`, `TASKS.md`, architecture docs, PR comments, and fleeting chat histories.
- Feeding entire markdown files to LLMs repeatedly wastes context window tokens and leads to conflicting instructions or lost decisions over time.

**Anchor solves this by storing durable project choices in a lightweight, local SQLite database (`.anchor/anchor.db`) and exposing them directly to AI agents via the Model Context Protocol (MCP).**

> **Core Rule:** Store *durable decisions and operational notes*, not redundant descriptions of the entire codebase.

```text
               ┌─────────────┐
               │  User Prompt│
               └──────┬──────┘
                      │
                      ▼
            ┌───────────────────┐
            │   Coding Agent    │
            │ (Claude / Cursor) │
            └─────────┬─────────┘
                      │ (MCP over STDIO)
                      ▼
              ╔═══════════════╗
              ║    Anchor     ║
              ║  (SQLite FTS) ║
              ╚═══════════════╝
```

---

## ✨ Features

- ⚡ **Local-First & Fast:** Runs on local SQLite with built-in FTS5 full-text indexing. Zero cloud or background database dependencies.
- 🤖 **Universal MCP Integration:** Compatible with any MCP-enabled agent (Claude Code, Cursor, Antigravity, OpenCode, Codex).
- 🎯 **Task-Oriented Context Retrieval:** Agents query `anchor_context` before planning to retrieve only the relevant decisions and constraints.
- 🔒 **Atomic Mutations & Batch Operations:** Update, soft-delete, or apply multi-record mutations in single atomic transactions.
- 🪶 **Zero Semantic Bloat:** No vector databases or embeddings needed—the coding agent handles semantic reasoning, Anchor handles deterministic memory.
- 📁 **Non-Destructive Integration:** Automatically maintains `AGENTS.md` and `CLAUDE.md` managed instruction blocks without overwriting existing guidelines.

---

## 🚀 Quick Installation

### Windows (PowerShell)

Install globally with one command:

```powershell
irm https://raw.githubusercontent.com/yosef-atta/anchor/main/setup.ps1 | iex
```

Or clone and run the installer locally:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### With `uv` or `pip`

```bash
# Using uv (recommended)
uv tool install .

# Or using standard pip
pip install .
```

Verify your installation:

```bash
anchor --version
```

---

## ⚡ Quick Start (30 Seconds)

### 1. Initialize a Repository

Run `anchor init` inside your project directory:

```bash
anchor init
```

This creates:
- `.anchor/anchor.db` (Local SQLite database with FTS5 search)
- `.anchor/.gitignore` (Prevents tracking local database lock artifacts)
- Agent rule anchors in `AGENTS.md` and `CLAUDE.md`

### 2. Configure Your AI Agent (MCP)

Add Anchor to your agent's MCP configuration file (e.g. `mcp.json` or agent settings):

```json
{
  "mcpServers": {
    "anchor": {
      "command": "anchor",
      "args": ["mcp"]
    }
  }
}
```

### 3. Check Status

```bash
anchor status
```

---

## 🛠️ CLI Usage

| Command | Description | Example |
| :--- | :--- | :--- |
| `anchor init [path]` | Initialize Anchor in a repo | `anchor init .` |
| `anchor status [path]` | Display project stats & record counts | `anchor status` |
| `anchor add decision` | Record a durable technical decision | See below |
| `anchor add note` | Record persistent project context | See below |
| `anchor context <query>` | Retrieve relevant context for a task | `anchor context "database migration"` |
| `anchor search <query>` | Full-text search across all memory | `anchor search "auth"` |
| `anchor get <id>` | Fetch a specific record by ID | `anchor get D-000001` |
| `anchor edit <id>` | Update fields on an existing record | See below |
| `anchor delete <id>` | Soft-delete a decision or note | `anchor delete N-000002` |
| `anchor apply <file.json>` | Apply atomic batch of mutations | `anchor apply batch.json` |
| `anchor bootstrap complete` | Complete existing-project bootstrap | `anchor bootstrap complete` |
| `anchor mcp` | Start STDIO MCP server for AI agents | `anchor mcp` |

### Adding Memory Records

```bash
# Add a decision
anchor add decision \
  --title "Primary database" \
  --category "database" \
  --decision "Use PostgreSQL as primary relational database." \
  --reason "Requires JSONB support and pgvector compatibility."

# Add a context note
anchor add note \
  --title "Local Dev Database" \
  --category "environment" \
  --text "PostgreSQL runs through Docker Compose on port 5432."
```

### Editing and Querying

```bash
# Edit a decision
anchor edit D-000001 --decision "Use PostgreSQL 16+" --reason "Performance improvements."

# Retrieve task context as JSON
anchor context "PostgreSQL setup" --json
```

---

## 🤖 MCP Tools Reference

When running `anchor mcp`, the following tools are exposed directly to AI coding agents:

| Tool | Purpose |
| :--- | :--- |
| `anchor_status` | Returns project metadata, initialization state, and record counts. |
| `anchor_context` | Retrieves task-relevant Decisions and Notes for pre-implementation planning. |
| `anchor_search` | Performs full-text keyword search across memory with pagination support. |
| `anchor_get` | Looks up a specific Decision (`D-xxxxxx`) or Note (`N-xxxxxx`) by stable ID. |
| `anchor_add_decision`| Stores a persistent technical decision made by the user/agent. |
| `anchor_add_note` | Stores operational context, ports, dev notes, and constraints. |
| `anchor_edit` | Modifies fields of an existing record while preserving history. |
| `anchor_delete` | Soft-deletes a record so it is excluded from search & context by default. |
| `anchor_apply_batch` | Executes a list of mutations atomically in a single SQLite transaction. |
| `anchor_complete_bootstrap` | Transitions an existing project from `pending` to `complete` bootstrap status. |

---

## 🧠 Memory Structure

### Decision Record (`D-xxxxxx`)
```text
• id          : Stable sequential ID (e.g. D-000001)
• title       : Short descriptive title
• category    : Category grouping (e.g. database, auth, api)
• decision    : The exact choice made
• reason      : Rationale behind the decision
• origin      : live | bootstrap
• timestamps  : created_at, updated_at, deleted_at
```

### Note Record (`N-xxxxxx`)
```text
• id          : Stable sequential ID (e.g. N-000001)
• title       : Short descriptive title
• category    : Category grouping (e.g. dev, tooling, config)
• text        : Informational note content
• origin      : live | bootstrap
• timestamps  : created_at, updated_at, deleted_at
```

---

## 🧪 Development & Testing

Anchor uses `uv` for fast, reproducible development:

```bash
# Clone the repository
git clone https://github.com/yosef-atta/anchor.git
cd anchor

# Run test suite
uv run pytest

# Lint and check types
uv run ruff check .
uv run pyright
```

---

## 📄 License

MIT © [Yosef Atta](https://github.com/yosef-atta)
