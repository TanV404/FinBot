---
description: "Create and manage Architecture Decision Records (ADRs) at the project level, optionally extracting from feature research"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Create, update, or query Architecture Decision Records (ADRs) stored at `.specify/decisions/`. ADRs capture significant architectural and technical decisions with their context, rationale, and consequences. Decisions can be created from scratch or promoted from feature-level `research.md` findings.

## Operating Constraints

- **Writes to `.specify/decisions/`**: Creates/updates ADR files and index.
- **May update graph**: If dependency graph exists, adds decision nodes with `constrains` edges.
- **Project-level**: ADRs persist across features and capture project-wide decisions.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries about architectural decisions, tech stack issues, or decision regret

### 1. Determine Action

Parse `$ARGUMENTS` to determine the operation:

- **No arguments or `new`**: Create a new ADR interactively
- **`promote`**: Extract decisions from a feature's `research.md` and promote to project-level ADRs
- **`list`**: Display all ADRs with their status
- **`update ADR-NNN`**: Update the status of an existing ADR
- **`query KEYWORD`**: Search ADRs by keyword, technology, or component

### 2. For New ADR (interactive)

Ask the user:

1. "What decision needs to be recorded?" (brief title)
2. "What is the context? Why is this decision needed?"
3. "What was decided?"
4. "What alternatives were considered?"
5. "What are the consequences of this decision?"
6. "Which features or components does this affect?"

### 3. For Promote from Research

1. Load the current feature's `research.md` (or specified feature's)
2. Parse decisions: look for "Decision:", "Rationale:", "Alternatives:" patterns
3. For each decision found, create an ADR if no similar project-level ADR exists
4. Ask user to confirm each promotion: "Promote this decision to project-level ADR?"

### 4. Assign ADR Number

- Scan `.specify/decisions/` for existing ADR files
- Find the highest ADR number
- Assign the next sequential number (ADR-001, ADR-002, etc.)

### 5. Write ADR

Load `.specify/templates/adr-template.md` and populate. Write to `.specify/decisions/ADR-NNN-short-title.md`.

### 6. Update Index

Read `.specify/decisions/index.md` and add the new ADR entry:

```markdown
| ADR-NNN | [Title] | [Status] | [Date] | [Features] |
```

### 7. Update Dependency Graph (if exists)

If `.specify/graphs/index.json` exists:

- Add a decision node: `type: "decision"`, ID: `ADR-NNN`
- For each affected component mentioned in the ADR:
  - Add `constrains` edge from ADR node to the component node
- Write updated graph

### 8. Report

Output:
- Path to created/updated ADR
- Summary: title, status, affected components
- If dependencies found: "This decision constrains [N] components across [M] features"
- Next steps: "Communicate this decision to affected teams"

## For List Action

Display all ADRs:

```markdown
## Architecture Decision Records

| ID | Title | Status | Date | Affected Components |
|----|-------|--------|------|-------------------|
| ADR-001 | Use PostgreSQL | Accepted | 2026-01-15 | Database, ORM, Migrations |
| ADR-002 | REST over GraphQL | Accepted | 2026-01-20 | All API endpoints |
| ADR-003 | Monorepo structure | Proposed | 2026-02-10 | Build system, CI/CD |
```

## For Update Action

1. Load the specified ADR
2. Valid status transitions:
   - Proposed → Accepted / Rejected
   - Accepted → Deprecated / Superseded
   - Deprecated → (terminal)
   - Superseded → (terminal, must link to superseding ADR)
3. Update status and add amendment note
4. If Superseded: create link to new ADR

## For Query Action

Search ADR content for the keyword and return matching ADRs with relevant excerpts.

## Guidelines

- ADRs should be concise: 1-2 pages maximum
- Focus on the "why", not just the "what"
- Every ADR should be findable by technology name, component name, or decision topic
- Deprecated/Superseded ADRs stay in the index for historical context
- Reference specific spec or research files that prompted the decision
