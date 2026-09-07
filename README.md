# Anchor

Anchor is a local project-memory and decision system built for agentic software development.

Instead of spreading project decisions across `PRD.md`, `TASKS.md`, architecture documents, specs, comments, and chat history, Anchor stores durable project knowledge in a local SQLite database and exposes it directly to coding agents through MCP.

The goal is simple:

> Give coding agents persistent project memory without turning the repository into a documentation warehouse.

---

## Why Anchor Exists

Agentic coding workflows usually rely on Markdown files such as:

* `PRD.md`
* `TASKS.md`
* architecture documents
* specs
* ADRs
* agent instruction files

These approaches work, but they tend to create two problems.

### 1. Overdocumentation

A project can quickly accumulate large amounts of documentation that the coding agent must repeatedly read and reconcile.

Many implementation details become duplicated across multiple files even when they do not need to be permanent project knowledge.

### 2. Distributed decisions

A single project decision may appear in many places.

For example, a project may originally plan to use MySQL.

Before backend implementation begins, the team decides to use PostgreSQL instead.

That should be one simple change.

In a heavily documented workflow, however, the database choice may already exist in:

* the PRD
* architecture documentation
* implementation specs
* task files
* stack documentation
* agent instructions

Changing one decision can therefore require updating many unrelated artifacts.

Anchor treats the decision itself as the source of truth.

---

# Core Idea

Anchor stores two primary kinds of project memory:

## Decisions

Durable choices that future coding agents should understand and respect.

Examples:

* Use PostgreSQL as the primary relational database.
* Store authentication sessions in HTTP-only cookies.
* Use pnpm as the project package manager.
* API handlers must not access the database directly.

A decision contains:

* title
* category
* decision
* reason

---

## Notes

Useful project knowledge that should persist but is not necessarily a decision.

Examples:

* Local PostgreSQL runs through Docker Compose.
* Stripe test webhooks require a local tunnel.
* The frontend dev server runs on port 3000.

A note contains:

* title
* category
* text

---

# What Anchor Is Not

Anchor is not intended to become another documentation system.

The goal is not to record everything about the project.

Anchor should store the smallest useful set of durable information that could prevent a future coding agent from making a wrong assumption or conflicting implementation.

A useful rule is:

> Store decisions, not descriptions of the entire system.

Routine implementation details should remain in the code.

---

# Architecture

Anchor has two interfaces over the same core.

```text
CLI ─────┐
         │
         ▼
     Anchor Core ───── SQLite
         ▲
         │
MCP ─────┘
```

The CLI and MCP server must use the same application logic.

Neither interface should implement separate business rules.

---

# Technology Stack

Anchor is intentionally small and local-first.

## Runtime

* Python 3.12+

## Package Management

* uv

## CLI

* Typer
* Rich

## Validation

* Pydantic

## Storage

* SQLite
* Python `sqlite3`
* SQLite FTS5

## MCP

* Official Python MCP SDK
* STDIO transport

## Testing

* pytest

## Code Quality

* Ruff
* Pyright

Anchor does not require:

* FastAPI
* Uvicorn
* PostgreSQL
* Redis
* Docker
* a vector database
* embeddings
* an external LLM
* an HTTP server

The coding agent itself provides semantic reasoning.

---

# Installation

The intended installation flow is a PowerShell setup script.

Example:

```powershell
irm https://raw.githubusercontent.com/<owner>/anchor/main/setup.ps1 | iex
```

The setup script installs Anchor and makes the `anchor` command available globally.

Verify the installation:

```powershell
anchor --version
```

---

# Initialize a Project

Run Anchor from the project root:

```powershell
anchor init
```

This is equivalent to:

```powershell
anchor init .
```

You can also provide another project path:

```powershell
anchor init F:\projects\example
```

Anchor is completely non-interactive.

It must never ask questions or wait for terminal input.

On success, Anchor creates:

```text
project/
├── .anchor/
│   └── anchor.db
├── AGENTS.md
└── CLAUDE.md
```

The database contains project memory and Anchor metadata.

`AGENTS.md` and `CLAUDE.md` explain the Anchor workflow to coding agents.

---

# MCP Setup

Anchor does not contain integrations for individual coding tools.

It does not need to know whether the user runs:

* Codex
* Claude Code
* Antigravity
* OpenCode
* Pi
* Cursor
* another MCP-compatible coding agent

Anchor integrates with MCP, not with specific coding agents.

After initialization, Anchor prints the MCP configuration:

```text
Name:
anchor

Transport:
stdio

Command:
anchor

Arguments:
mcp
```

The user adds this MCP server manually to their preferred coding tool.

The coding tool then launches:

```powershell
anchor mcp
```

Anchor communicates with the coding agent through STDIO.

No HTTP server or FastAPI application is required.

---

# Agent Workflow

Anchor is designed so that the coding agent performs semantic reasoning while Anchor provides persistence and deterministic operations.

## Before Planning or Implementation

For meaningful project changes, the agent should:

1. Retrieve relevant Anchor context.
2. Review existing decisions and notes.
3. Check whether the proposed plan conflicts with existing project memory.
4. Surface meaningful conflicts to the user before implementation.
5. If the user changes an existing decision, update Anchor.
6. If the user keeps the existing decision, revise the implementation plan.

Example:

```text
User:
Replace PostgreSQL with MySQL.

Agent:
    ↓
anchor_context("replace PostgreSQL with MySQL")
    ↓
Relevant decisions and notes returned
    ↓
Agent identifies affected project memory
    ↓
Agent discusses conflicts with user if necessary
    ↓
Agent updates Anchor
    ↓
Implementation begins
```

Anchor does not attempt to understand the semantic meaning of PostgreSQL versus MySQL.

That reasoning belongs to the coding agent.

---

# Recording New Project Memory

When a durable choice is made, the agent should store a Decision.

When useful non-decision knowledge should persist, the agent should store a Note.

The agent should not record every implementation choice.

A useful test is:

> Would another coding agent be likely to make a wrong decision later if this information disappeared?

If not, it probably does not belong in Anchor.

---

# Existing Projects

Anchor must also support projects that already contain code, documentation, architecture decisions, and undocumented conventions.

This is treated as a bootstrap workflow.

After:

```powershell
anchor init
```

Anchor can identify that the project already contains existing files and mark the project as requiring bootstrap.

The coding agent then inspects:

* source code
* configuration
* package files
* infrastructure
* existing documentation
* specs
* comments
* existing conventions

The agent reconstructs only the smallest useful set of durable project decisions and notes.

---

## Bootstrap Rules

The agent must distinguish between:

### Observed Facts

Facts directly visible in the repository.

Example:

```text
The project currently uses PostgreSQL through Prisma.
```

### Inferred Decisions

Choices that appear intentional but whose rationale is not known.

Example:

```text
The project uses HTTP-only cookies for authentication.
```

### Known Rationale

Reasons explicitly found in documentation or provided by the user.

Example:

```text
PostgreSQL was chosen because the project requires JSONB and pgvector.
```

The agent must never invent historical reasoning.

If the reason cannot be recovered, Anchor should store it as unknown rather than create a plausible explanation.

---

# Bootstrap Review

Before writing recovered project memory, the agent should present a review to the user.

Example:

```text
Anchor Bootstrap Review

1. Primary database

Current state:
PostgreSQL is used through Prisma.

Reason:
Unknown.

Question:
Why was PostgreSQL chosen?


2. Authentication storage

Current state:
Authentication uses HTTP-only cookies.

Reason:
Unknown.

Question:
Was this primarily a security decision?


3. Package manager

Current state:
pnpm is used and pnpm-lock.yaml is committed.

Suggested decision:
Use pnpm as the project package manager.


4. Local database

Suggested note:
Local development runs PostgreSQL through Docker Compose.
```

The user can:

* confirm
* correct
* reject
* provide missing reasons
* add additional notes

The agent then writes the approved memory to Anchor.

---

# CLI

The Proof of Concept intentionally keeps the CLI surface small.

## Initialize Anchor

```powershell
anchor init [path]
```

---

## Start the MCP Server

```powershell
anchor mcp
```

Normally this command is launched by the configured MCP client.

---

## Project Status

```powershell
anchor status
```

Example output:

```text
project: F:\projects\example
initialized: true
project_type: existing
bootstrap_status: pending
decisions: 0
notes: 0
```

---

## Add a Decision

```powershell
anchor add decision `
  --title "Primary database" `
  --category "database" `
  --decision "Use PostgreSQL." `
  --reason "Required for JSONB and pgvector."
```

---

## Add a Note

```powershell
anchor add note `
  --title "Local database" `
  --category "development" `
  --text "PostgreSQL runs through Docker Compose on port 5432."
```

---

## Get a Record

```powershell
anchor get D-000001
```

or:

```powershell
anchor get N-000001
```

---

## Search Project Memory

```powershell
anchor search "database"
```

Pagination:

```powershell
anchor search "database" --page 2
```

Search returns compact results containing:

* ID
* type
* category
* title

The default page contains up to 20 records.

---

## Retrieve Context

```powershell
anchor context "replace PostgreSQL with MySQL"
```

`context` is intended primarily for coding agents.

Unlike `search`, it returns relevant records with their full useful content so the agent can reason about the requested change.

---

## Edit a Record

```powershell
anchor edit D-000001 `
  --decision "Use MySQL." `
  --reason "Production infrastructure requires MySQL."
```

Only provided fields are changed.

---

## Delete a Record

```powershell
anchor delete D-000001
```

Deletion is non-interactive.

The PoC uses soft deletion internally.

---

## Apply Multiple Changes Atomically

```powershell
anchor apply .\anchor-mutation.json
```

Example mutation:

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

All operations are executed in one SQLite transaction.

If any operation fails, the entire batch is rolled back.

---

# MCP Tools

The PoC exposes the following tools.

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

The MCP tools and CLI commands call the same Anchor Core.

---

# CLI and MCP Mapping

| Operation             | CLI                   | MCP                   |
| --------------------- | --------------------- | --------------------- |
| Initialize project    | `anchor init`         | —                     |
| Start MCP server      | `anchor mcp`          | —                     |
| Read project state    | `anchor status`       | `anchor_status`       |
| Add decision          | `anchor add decision` | `anchor_add_decision` |
| Add note              | `anchor add note`     | `anchor_add_note`     |
| Get record            | `anchor get`          | `anchor_get`          |
| Search memory         | `anchor search`       | `anchor_search`       |
| Retrieve task context | `anchor context`      | `anchor_context`      |
| Edit record           | `anchor edit`         | `anchor_edit`         |
| Delete record         | `anchor delete`       | `anchor_delete`       |
| Atomic batch          | `anchor apply`        | `anchor_apply_batch`  |

---

# Project Memory Model

## Decision

Conceptually:

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

Possible origins:

```text
live
bootstrap
```

---

## Note

Conceptually:

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

---

# Search

The Proof of Concept uses SQLite FTS5.

Indexed content includes:

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

Anchor and the coding agent deliberately have different responsibilities.

## Anchor Owns

* persistent project memory
* SQLite storage
* record IDs
* retrieval
* validation
* transactions
* atomic batch changes
* bootstrap state
* deterministic behavior

## The Coding Agent Owns

* semantic understanding
* identifying conflicts
* determining affected records
* interpreting project intent
* deciding whether something is a Decision or Note
* determining whether existing memory must change
* presenting conflicts and bootstrap questions to the user

Anchor is not an AI agent.

Anchor makes an AI coding agent stateful and project-aware.

---

# Non-Interactive by Design

Anchor is built for coding agents.

Every CLI command must therefore be fully non-interactive.

Anchor must never:

* ask confirmation questions
* display selection menus
* wait for terminal input
* launch a TUI
* require an interactive setup wizard

Invalid input must return a clear error and a non-zero exit code.

---

# PoC Scope

The Proof of Concept intentionally does not include:

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

The intended experience is:

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

---

# Status

Anchor is currently being designed as a Proof of Concept.

The initial goal is to validate one question:

> Can persistent structured project memory make agentic coding more reliable without introducing the documentation overhead that existing spec-heavy workflows create?

If the answer is yes, the system can evolve from real usage rather than speculative complexity.
