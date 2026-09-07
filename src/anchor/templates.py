"""Templates for AGENTS.md and CLAUDE.md generated during anchor init."""

ANCHOR_BLOCK_START = "<!-- anchor:start -->"
ANCHOR_BLOCK_END = "<!-- anchor:end -->"

ANCHOR_GUIDELINES = """# Anchor Project Memory

This repository uses **Anchor** as its persistent project-memory and decision system for AI coding agents.

Anchor stores durable project decisions and useful persistent notes in `.anchor/anchor.db` and exposes them through MCP.

Anchor is not a replacement for source code, normal documentation, or implementation details. Store only information that future agents may need in order to avoid incorrect assumptions, conflicting implementation choices, or loss of important project context.

## Before Planning or Implementation

Before planning or implementing any meaningful architectural, stack, behavioral, persistence, authentication, infrastructure, API, or project-wide change:

1. Retrieve relevant Anchor context using `anchor_context`.
2. Use `anchor_search` or `anchor_get` when more precise lookup is required.
3. Review all relevant Decisions and Notes before finalizing the plan.
4. Do not knowingly implement a solution that conflicts with an existing Anchor Decision.

Routine, local, or trivial code changes do not require unnecessary Anchor lookups.

## Handling Conflicts

If the requested work conflicts with an existing Anchor Decision:

1. Do not silently ignore or violate the Decision.
2. Explain the conflict clearly to the user before implementation.
3. Ask whether the existing Decision should change.

If the user approves changing the Decision:

- Update Anchor first.
- Identify any other Decisions or Notes affected by the change.
- Update all affected records consistently.
- Prefer `anchor_apply_batch` when multiple records must change together.
- Only continue implementation once Anchor memory is coherent.

If the user does not want to change the existing Decision:

- Keep the Decision unchanged.
- Revise the implementation plan so it complies with the existing Anchor memory.

If the user provides a different solution or direction, follow the user's latest explicit instruction and update Anchor when it represents a durable change.

## Recording Decisions

Use `anchor_add_decision` when a durable project choice is made that future agents should understand or preserve.

Examples include:

- primary database or persistence strategy
- authentication or session strategy
- architectural boundaries
- package-manager choice
- important framework or infrastructure choices
- project-wide behavioral constraints
- conventions whose violation could cause incorrect future implementation

A Decision should capture:

- what was decided
- why it was decided

Do not create Decisions for routine implementation details that are already obvious from the code and unlikely to influence future work.

## Recording Notes

Use `anchor_add_note` for persistent project knowledge that is useful but is not a durable decision.

Examples include:

- important local-development requirements
- non-obvious environment behavior
- operational constraints
- external tooling requirements
- useful project context that future agents may otherwise lose

Do not store transient debugging information, temporary task state, or trivial facts.

## Existing Project Bootstrap

If `anchor_status` reports that bootstrap is pending, treat the repository as an existing project whose important memory needs to be reconstructed before substantial new work.

Inspect relevant:

- source code
- configuration
- package manifests and lockfiles
- infrastructure files
- existing documentation
- specifications
- comments
- established project conventions

Recover only the smallest useful set of durable Decisions and Notes.

Do not attempt to document the entire existing project.

For each discovered item, distinguish between:

1. **Observed fact** — directly supported by the current repository.
2. **Known rationale** — the reason is explicitly documented or provided by the user.
3. **Unknown rationale** — the current choice is visible, but the reason cannot be recovered.

Never invent historical reasoning.

If a reason is unknown, explicitly treat it as unknown and ask the user when the reason materially matters.

Before writing bootstrap memory:

1. Present the proposed Decisions and Notes to the user.
2. Clearly identify unknown or uncertain rationale.
3. Let the user confirm, correct, reject, or add context.
4. Store only the approved memory.
5. Prefer `anchor_apply_batch` so the initial bootstrap state is written atomically.

## Editing or Deleting Anchor Memory

Before editing or deleting an existing Decision or Note:

1. Retrieve relevant context.
2. Identify other records that may be affected.
3. Do not leave known contradictory or stale Anchor memory behind.
4. Use `anchor_apply_batch` when multiple related records need to change together.

Use `anchor_edit` for isolated changes.

Use `anchor_delete` only when a record is genuinely no longer valid or useful.

## Available Anchor MCP Tools

- `anchor_status` — Read Anchor project status and bootstrap state.
- `anchor_context` — Retrieve relevant Decisions and Notes for an intended task or change.
- `anchor_search` — Search Anchor memory.
- `anchor_get` — Retrieve the full contents of a Decision or Note by ID.
- `anchor_add_decision` — Store a new durable Decision.
- `anchor_add_note` — Store a persistent Note.
- `anchor_edit` — Modify an existing record.
- `anchor_delete` — Soft-delete a record.
- `anchor_apply_batch` — Atomically apply multiple additions, edits, or deletions.

## Core Principle

Use Anchor to preserve the minimum durable project memory needed for future agents to work consistently.

Do not turn Anchor into another documentation warehouse.

A useful test before storing something is:

> Would a future coding agent be likely to make a wrong assumption or conflicting implementation if this information disappeared?

If the answer is no, it probably does not belong in Anchor."""

ANCHOR_FULL_BLOCK = f"{ANCHOR_BLOCK_START}\n\n{ANCHOR_GUIDELINES}\n\n{ANCHOR_BLOCK_END}\n"
