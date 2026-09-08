# Anchor

Anchor is a local project-memory and decision system built for agentic software development.

Instead of spreading durable project decisions across `PRD.md`, `TASKS.md`, architecture documents, specs, comments, and chat history, Anchor stores the smallest useful set of persistent project knowledge in a local SQLite database and exposes it to coding agents through MCP.

The goal is simple:

> Give coding agents persistent project memory without turning the repository into a documentation warehouse.

---

# Current Project Status

Anchor is an early Proof of Concept under active implementation.

## Implemented now

The current codebase implements the project foundation:

- `anchor init [path]`
- `anchor status [path]`
- project-root discovery
- `.anchor/anchor.db` creation
- `.anchor/.gitignore` creation
- SQLite schema initialization
- project metadata (`project_type`, `bootstrap_status`, `initialized_at`, schema version)
- Decision and Note tables
- SQLite FTS5 table creation
- `AGENTS.md` and `CLAUDE.md` Anchor-managed instruction blocks
- safe re-running of `anchor init` without replacing unrelated content in those agent files
- detection of new vs existing projects
- printing the intended MCP server configuration after initialization
- tests for the implemented `init` and `status` behavior

## Not implemented yet

The README describes the intended PoC surface, but the following commands and MCP tools are still roadmap items:

- `anchor add decision`
- `anchor add note`
- `anchor get`
- `anchor search`
- `anchor context`
- `anchor edit`
- `anchor delete`
- `anchor apply`
- `anchor mcp`
- all `anchor_*` MCP tools
- the complete existing-project bootstrap lifecycle
- the final PowerShell installation script

Until a roadmap phase is marked complete, examples for those features below should be read as the target interface rather than current functionality.

---

# Implementation Roadmap

The roadmap is intentionally ordered by dependency. Each phase should be finished and tested before starting the next one.

The guiding rule is:

> Build the project-memory lifecycle in the Core first, then expose the same behavior through CLI and MCP.

## Phase 0 — Project Foundation ✅

**Status: complete**

Implemented:

- package and CLI foundation
- SQLite database initialization
- metadata and memory schema
- FTS5 table creation
- Anchor project-root discovery
- `anchor init`
- `anchor status`
- new/existing project detection
- `AGENTS.md` / `CLAUDE.md` managed blocks
- initial tests

**Definition of done:** already satisfied by the current repository state.

---

## Phase 1 — Memory Write Foundation ✅

Implement the first real project-memory operations:

```text
anchor add decision
anchor add note
```

Core work:

- Pydantic input models and validation
- deterministic sequential IDs such as `D-000001` and `N-000001`
- UTC timestamps
- `origin` handling (`live` / `bootstrap`)
- transaction-safe inserts
- FTS index insertion in the same logical operation
- duplicate/error handling with clear non-zero CLI exits

Tests must cover:

- valid Decision creation
- valid Note creation
- required fields
- ID sequencing
- timestamp/origin behavior
- transaction rollback on failure
- FTS row creation

**Why first:** every read, search, context, edit, delete, and batch operation needs records to exist before it can be meaningfully implemented.

---

## Phase 2 — Deterministic Read Operations

Implement:

```text
anchor get <id>
anchor search <query>
```

Core work:

- record lookup by stable ID
- Decision/Note normalization
- soft-deleted records excluded by default
- FTS5 query execution
- compact search-result shape
- deterministic ordering
- pagination with a default page size of 20
- safe handling of empty and malformed queries

Tests must cover:

- Decision lookup
- Note lookup
- unknown IDs
- deleted records
- exact and partial search matches
- pagination
- deterministic ordering

**Why before `context`:** `context` should be built on a proven retrieval layer, not become a second independent search implementation.

---

## Phase 3 — Task-Oriented Context Retrieval

Implement:

```text
anchor context "task description"
```

Target behavior:

- reuse the same retrieval primitives as `anchor search`
- return full useful record content instead of compact rows
- return Decisions and Notes in a stable machine-friendly structure
- keep semantic reasoning in the coding agent rather than Anchor
- avoid embeddings, vector search, or an internal LLM in the PoC

Tests must cover:

- relevant Decision retrieval
- relevant Note retrieval
- mixed results
- empty/no-match behavior
- stable response structure

**Design constraint:** `context` is retrieval, not an AI reasoning engine.

---

## Phase 4 — Mutation Lifecycle and Atomic Batch

Implement:

```text
anchor edit <id>
anchor delete <id>
anchor apply <mutation-file>
```

Core work:

- partial field updates
- updated timestamps
- soft deletion through `deleted_at`
- FTS synchronization after edit/delete
- validation that Decision-only and Note-only fields cannot be mixed
- batch mutation schema
- one SQLite transaction for the entire batch
- full rollback when any operation fails

Tests must cover:

- partial edits
- invalid edits
- soft deletion
- search behavior after edits/deletes
- multi-operation batch success
- rollback on any batch failure

**Why before MCP:** once this phase is complete, the Core exposes the complete PoC memory lifecycle. MCP can then remain a thin interface instead of containing unfinished business logic.

---

## Phase 5 — MCP Server and Tool Parity

Implement:

```text
anchor mcp
```

Expose:

```text
anchor_status
anchor_search
anchor_context
anchor_get
anchor_add_decision
anchor_add_note
anchor_edit
anchor_delete
anchor_apply_batch
```

Requirements:

- Official Python MCP SDK
- STDIO transport
- no HTTP server
- no agent-specific integration code
- MCP tools call the exact same Core functions as the CLI
- no duplicated validation or persistence rules in the MCP layer
- clear structured tool errors

Tests must cover:

- tool registration
- request/response schemas
- representative tool calls against a temporary Anchor project
- parity between CLI/Core and MCP behavior

At the end of this phase, the MCP configuration printed by `anchor init` becomes fully usable.

---

## Phase 6 — Existing-Project Bootstrap Lifecycle

Complete the behavior already started by `anchor init` for existing repositories.

Current behavior already sets:

```text
project_type: existing
bootstrap_status: pending
```

This phase must define and implement the missing lifecycle so a project does not remain `pending` forever.

Required behavior:

1. coding agent inspects the repository
2. agent distinguishes observed facts, inferred decisions, and known rationale
3. agent presents a bootstrap review to the user
4. approved Decisions and Notes are written with `origin = bootstrap`
5. bootstrap completion is recorded explicitly and deterministically
6. `anchor status` reports the completed state

Keep the completion mechanism minimal. Do not add a broad bootstrap subsystem or interactive wizard merely to change this state.

Tests must cover:

- pending bootstrap state
- bootstrap-origin records
- completion transition
- idempotent completion behavior

---

## Phase 7 — Installation, End-to-End QA, and PoC Validation

Finish the distribution path only after the CLI and MCP behavior are real.

Implement:

- PowerShell `setup.ps1`
- installation/update behavior needed to expose the global `anchor` command
- `anchor --version` verification flow
- clean-machine installation test
- full CLI integration tests
- MCP end-to-end test over STDIO
- README examples checked against real command output
- Ruff, Pyright, and pytest passing

Then validate the actual PoC workflow in one new project and one existing project:

```text
Install Anchor
    ↓
anchor init
    ↓
configure MCP
    ↓
add durable project memory
    ↓
retrieve context before implementation
    ↓
change a decision
    ↓
update Anchor atomically
    ↓
confirm a later coding-agent session receives the correct context
```

Only after this should new features outside the PoC scope be considered.

---

## Roadmap Summary

```text
0. Foundation                         ✅ complete
   init + status + schema + metadata + agent files

1. Memory writes                      ✅ complete
   add decision + add note

2. Deterministic reads
   get + search

3. Context retrieval
   context

4. Mutation lifecycle
   edit + delete + apply batch

5. MCP parity
   mcp server + all anchor_* tools

6. Existing-project bootstrap
   review/write/complete lifecycle

7. Distribution and validation
   setup.ps1 + E2E + PoC validation
```

Do not skip ahead because a later command looks easy. The ordering exists to keep storage, validation, retrieval, mutation, and MCP behavior from diverging.

---

# Why Anchor Exists

Agentic coding workflows commonly rely on Markdown files such as:

- `PRD.md`
- `TASKS.md`
- architecture documents
- specs
- ADRs
- agent instruction files

These approaches work, but they tend to create two problems.

## Overdocumentation

A project can quickly accumulate large amounts of documentation that the coding agent must repeatedly read and reconcile.

Many implementation details become duplicated across files even when they do not need to become permanent project knowledge.

## Distributed decisions

A single project decision may appear in many places.

For example, a project may originally plan to use MySQL and later change to PostgreSQL. In a heavily documented workflow that choice may already exist in a PRD, architecture docs, implementation specs, task files, and agent instructions.

Anchor treats the durable decision itself as the source of truth.

---

# Core Idea

Anchor stores two primary kinds of project memory.

## Decisions

Durable choices that future coding agents should understand and respect.

Examples:

- Use PostgreSQL as the primary relational database.
- Store authentication sessions in HTTP-only cookies.
- Use pnpm as the project package manager.
- API handlers must not access the database directly.

A Decision contains:

```text
id
title
category
decision
reason
origin
created_at
updated_at
deleted_at
```

## Notes

Useful project knowledge that should persist but is not necessarily a decision.

Examples:

- Local PostgreSQL runs through Docker Compose.
- Stripe test webhooks require a local tunnel.
- The frontend dev server runs on port 3000.

A Note contains:

```text
id
title
category
text
origin
created_at
updated_at
deleted_at
```

Possible origins:

```text
live
bootstrap
```

---

# What Anchor Is Not

Anchor is not intended to become another documentation system.

The goal is not to record everything about a project. Anchor should store the smallest useful set of durable information that could prevent a future coding agent from making a wrong assumption or conflicting implementation.

A useful rule is:

> Store decisions, not descriptions of the entire system.

Routine implementation details should remain in the code.

---

# Architecture

Anchor has two interfaces over the same Core:

```text
CLI ─────┐
         │
         ▼
     Anchor Core ───── SQLite
         ▲
         │
MCP ─────┘
```

The CLI and MCP server must use the same application logic. Neither interface should implement separate business rules.

---

# Technology Stack

Anchor is intentionally small and local-first.

- Python 3.12+
- uv
- Typer
- Rich
- Pydantic
- SQLite through Python `sqlite3`
- SQLite FTS5
- Official Python MCP SDK
- STDIO MCP transport
- pytest
- Ruff
- Pyright

Anchor does not require:

- FastAPI
- Uvicorn
- PostgreSQL
- Redis
- Docker
- a vector database
- embeddings
- an external LLM
- an HTTP server

The coding agent itself provides semantic reasoning.

---

# Installation

The final intended installation flow is a PowerShell setup script, but `setup.ps1` is not implemented yet. It is scheduled for Roadmap Phase 7.

Target usage:

```powershell
irm https://raw.githubusercontent.com/yosef-atta/anchor/main/setup.ps1 | iex
```

Target verification:

```powershell
anchor --version
```

For development, use the repository's uv-based environment until the installer exists.

---

# Initialize a Project

`anchor init` is implemented now.

From the project root:

```powershell
anchor init
```

Equivalent:

```powershell
anchor init .
```

Another path can also be provided:

```powershell
anchor init F:\projects\example
```

Anchor is non-interactive. It must never ask questions or wait for terminal input.

Initialization creates or maintains:

```text
project/
├── .anchor/
│   ├── .gitignore
│   └── anchor.db
├── AGENTS.md
└── CLAUDE.md
```

`AGENTS.md` and `CLAUDE.md` contain an Anchor-managed block while preserving unrelated existing content.

---

# Project Status

`anchor status` is implemented now.

```powershell
anchor status
```

Example:

```text
project: F:\projects\example
initialized: true
project_type: existing
bootstrap_status: pending
decisions: 0
notes: 0
```

Anchor searches upward for the nearest `.anchor/anchor.db`, so status can be called from a subdirectory inside an initialized project.

---

# MCP Setup

Anchor integrates with MCP rather than individual coding tools.

It does not need agent-specific integrations for Codex, Claude Code, Antigravity, OpenCode, Pi, Cursor, or another MCP-compatible coding agent.

`anchor init` currently prints the intended MCP configuration:

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

The `anchor mcp` command itself is planned for Roadmap Phase 5 and is not implemented yet.

Once implemented, communication will use STDIO. No HTTP server or FastAPI application is required.

---

# Target CLI

The PoC target surface is intentionally small.

Implemented today:

```powershell
anchor init [path]
anchor status [path]
```

Planned by the roadmap:

```powershell
anchor add decision `
  --title "Primary database" `
  --category "database" `
  --decision "Use PostgreSQL." `
  --reason "Required for JSONB and pgvector."
```

```powershell
anchor add note `
  --title "Local database" `
  --category "development" `
  --text "PostgreSQL runs through Docker Compose on port 5432."
```

```powershell
anchor get D-000001
anchor get N-000001
anchor search "database"
anchor search "database" --page 2
anchor context "replace PostgreSQL with MySQL"
```

```powershell
anchor edit D-000001 `
  --decision "Use MySQL." `
  --reason "Production infrastructure requires MySQL."
```

```powershell
anchor delete D-000001
```

```powershell
anchor apply .\anchor-mutation.json
```

Example target batch file:

```json
{
  "operations": [
    {
      "action": "edit",
      "id": "D-000018",
      "changes": {
        "decision": "Use MySQL.",
        "reason": "Production infrastructure requires MySQL."
      }
    },
    {
      "action": "edit",
      "id": "N-000009",
      "changes": {
        "text": "MySQL runs through Docker Compose on port 3306."
      }
    }
  ]
}
```

All batch operations must execute in one SQLite transaction. If any operation fails, the entire batch must roll back.

---

# Target MCP Tools

Roadmap Phase 5 will expose:

```text
anchor_status
anchor_search
anchor_context
anchor_get
anchor_add_decision
anchor_add_note
anchor_edit
anchor_delete
anchor_apply_batch
```

CLI and MCP must call the same Anchor Core.

| Operation | CLI | MCP |
| --- | --- | --- |
| Initialize project | `anchor init` | — |
| Start MCP server | `anchor mcp` | — |
| Read project state | `anchor status` | `anchor_status` |
| Add decision | `anchor add decision` | `anchor_add_decision` |
| Add note | `anchor add note` | `anchor_add_note` |
| Get record | `anchor get` | `anchor_get` |
| Search memory | `anchor search` | `anchor_search` |
| Retrieve task context | `anchor context` | `anchor_context` |
| Edit record | `anchor edit` | `anchor_edit` |
| Delete record | `anchor delete` | `anchor_delete` |
| Atomic batch | `anchor apply` | `anchor_apply_batch` |

---

# Agent Workflow

Anchor is designed so that the coding agent performs semantic reasoning while Anchor provides persistence and deterministic operations.

Before meaningful planning or implementation, the agent should:

1. retrieve relevant Anchor context
2. review existing Decisions and Notes
3. check whether the proposed plan conflicts with existing project memory
4. surface meaningful conflicts to the user before implementation
5. update Anchor if the user changes an existing decision
6. revise the implementation plan if the existing decision remains in force

Example target flow:

```text
User:
Replace PostgreSQL with MySQL.

Agent:
    ↓
anchor_context("replace PostgreSQL with MySQL")
    ↓
Relevant Decisions and Notes returned
    ↓
Agent identifies affected project memory
    ↓
Agent surfaces meaningful conflicts
    ↓
Approved Anchor records are updated
    ↓
Implementation begins
```

Anchor does not attempt to understand the semantic meaning of PostgreSQL versus MySQL. That reasoning belongs to the coding agent.

---

# Recording New Project Memory

When a durable choice is made, the agent should store a Decision.

When useful non-decision knowledge should persist, the agent should store a Note.

The agent should not record every implementation choice.

A useful test is:

> Would another coding agent be likely to make a wrong decision later if this information disappeared?

If not, it probably does not belong in Anchor.

---

# Existing Projects and Bootstrap

Anchor must support projects that already contain code, documentation, architecture decisions, and undocumented conventions.

`anchor init` already detects an existing project and records:

```text
project_type: existing
bootstrap_status: pending
```

The complete recovery workflow is planned for Roadmap Phase 6.

The coding agent should inspect:

- source code
- configuration
- package files
- infrastructure
- existing documentation
- specs
- comments
- existing conventions

It should reconstruct only the smallest useful set of durable project Decisions and Notes.

## Bootstrap evidence rules

The agent must distinguish between:

### Observed facts

Facts directly visible in the repository.

```text
The project currently uses PostgreSQL through Prisma.
```

### Inferred decisions

Choices that appear intentional but whose rationale is not known.

```text
The project uses HTTP-only cookies for authentication.
```

### Known rationale

Reasons explicitly found in documentation or provided by the user.

```text
PostgreSQL was chosen because the project requires JSONB and pgvector.
```

The agent must never invent historical reasoning. If the reason cannot be recovered, it should remain unknown rather than be replaced with a plausible story.

Before recovered memory is written, the agent should present a review so the user can confirm, correct, reject, or provide missing rationale.

---

# Search Design

The PoC uses SQLite FTS5.

Indexed content is intended to include:

```text
title
category
decision
reason
text
```

No embeddings or vector database are required.

`anchor search` provides direct project-memory search.

`anchor context` provides task-oriented retrieval for coding agents.

The retrieval implementation can evolve later without changing the external Anchor workflow.

---

# Responsibility Boundary

## Anchor owns

- persistent project memory
- SQLite storage
- record IDs
- retrieval
- validation
- transactions
- atomic batch changes
- bootstrap state
- deterministic behavior

## The coding agent owns

- semantic understanding
- identifying conflicts
- determining affected records
- interpreting project intent
- deciding whether something is a Decision or Note
- determining whether existing memory must change
- presenting conflicts and bootstrap questions to the user

Anchor is not an AI agent.

Anchor makes an AI coding agent stateful and project-aware.

---

# Non-Interactive by Design

Every Anchor CLI command must be fully non-interactive.

Anchor must never:

- ask confirmation questions
- display selection menus
- wait for terminal input
- launch a TUI
- require an interactive setup wizard

Invalid input must return a clear error and a non-zero exit code.

---

# PoC Scope

The initial PoC intentionally does not include:

```text
anchor list
anchor restore
anchor history
anchor relations
anchor link
anchor unlink
anchor doctor
anchor upgrade
anchor migrate
anchor sync
anchor import
anchor export
anchor config
anchor stats
anchor validate
agent-specific setup commands
agent-specific integrations
HTTP MCP transport
embeddings
vector search
LLM integration
TUI
web interface
```

These features should only be added if real usage demonstrates that they are necessary.

---

# Design Principle

Anchor should remain smaller than the documentation system it replaces.

The project should resist adding commands, schemas, metadata, and workflows unless they solve an observed problem.

The intended end-state experience is:

```text
Install Anchor once
        ↓
Initialize a project once
        ↓
Configure the Anchor MCP server
        ↓
Work normally with the coding agent
        ↓
Anchor quietly preserves the decisions that matter
```

The PoC exists to answer one question:

> Can persistent structured project memory make agentic coding more reliable without introducing the documentation overhead that spec-heavy workflows create?

If the answer is yes, Anchor should evolve from real usage rather than speculative complexity.
