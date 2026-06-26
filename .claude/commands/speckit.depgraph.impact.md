---
description: "Analyze the impact of the current feature on existing features via the dependency graph"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Given the current feature's spec, plan, and/or tasks, identify all existing features, components, files, entities, and requirements that may be affected — highlighting potential conflict areas before implementation begins.

## Operating Constraints

- **Read source artifacts, write only to graph files**: Read specs, plans, tasks, and code. Only create/update dependency graph JSON files.
- **Graph-dependent**: This command requires `.specify/graphs/index.json` to exist. If it doesn't, instruct the user to run `/speckit.depgraph.discover` first.
- **Deterministic**: Re-running without changes should produce consistent results.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries about impact analysis, conflicts, or cross-feature issues
- Apply lessons learned from previous impact analysis runs

### 1. Initialize Context

Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS.

Verify `.specify/graphs/index.json` exists. If not:
- Error: "No dependency graph found. Run `/speckit.depgraph.discover` to bootstrap a graph from existing code, or run `/speckit.plan` on at least one feature to seed the graph."

### 2. Build Global Graph

1. Load `.specify/graphs/index.json` as the base graph
2. Scan all `specs/*/dependency-graph.json` files
3. Merge per-feature graphs into the global graph:
   - Add new nodes (skip duplicates by ID)
   - Add new edges (skip duplicate from+to+relation combinations)
   - Preserve external_dependencies from all features
4. Build lookup indexes:
   - **by-file**: Map file paths → list of nodes/features that reference them
   - **by-entity**: Map entity IDs → list of features that use them
   - **by-endpoint**: Map endpoint IDs → list of features that consume/produce them
   - **by-requirement**: Map requirement IDs → features

### 3. Analyze Current Feature's Footprint

Load the current feature's artifacts and extract its footprint:

**From spec.md** (if exists):
- Functional requirements (FR-xxx IDs)
- Key entities mentioned
- Success criteria / NFRs

**From plan.md** (if exists):
- File paths from project structure
- Data model entities and relationships
- API endpoints from contracts
- Technology dependencies

**From tasks.md** (if exists):
- File paths from task descriptions
- Entity references
- Endpoint references

**From dependency-graph.json** (if exists):
- All nodes and edges already mapped for this feature

### 4. Compute Impact Sets

For each touchpoint in the current feature, query the global graph:

**File Overlap**: Which existing features modify the same files?
- For each file the current feature plans to create/modify
- Query by-file index for other features touching the same file
- Severity: CRITICAL if both modify; HIGH if one reads and one modifies

**Entity Overlap**: Which existing features depend on the same entities?
- For each entity the current feature creates/extends/modifies
- Query by-entity index for other features using the same entity
- Severity: HIGH if schema changes; MEDIUM if read-only overlap

**Endpoint Overlap**: Which existing features share API endpoints?
- For each endpoint the current feature defines or modifies
- Query by-endpoint index for other features consuming the same endpoint
- Severity: MEDIUM if same endpoint with different contracts; LOW if compatible

**Requirement Conflicts**: Which existing requirements could be violated?
- Compare current feature's requirements against existing features
- Look for contradictions (e.g., different auth methods, conflicting constraints)
- Severity: CRITICAL if direct contradiction; HIGH if implicit conflict

**Transitive Impact**: Follow edges 2-3 hops deep
- If this feature changes Entity A, and Feature X's Task T045 depends on Entity A through Service B, flag the transitive path
- Severity: Based on hop distance — direct is higher, transitive is lower

### 5. Classify Conflicts

| Severity | Condition |
|----------|-----------|
| CRITICAL | Same file modified with incompatible changes; direct requirement contradiction |
| HIGH | Shared entity with schema changes; same API endpoint modified differently |
| MEDIUM | Read/write overlap on shared files; same endpoint with compatible changes |
| LOW | Transitive dependency (2+ hops); entity read-only overlap |

### 6. Produce Impact Analysis Report

Output a structured report:

```markdown
## Impact Analysis Report

**Feature**: [current feature name]
**Analyzed Against**: [N] existing features
**Generated**: [timestamp]
**Global Graph**: [N] nodes, [M] edges

### Conflict Summary

| Severity | Count |
|----------|-------|
| CRITICAL | [N] |
| HIGH | [N] |
| MEDIUM | [N] |
| LOW | [N] |

### Findings

| ID | Severity | This Feature | Conflicts With | Type | Details |
|----|----------|-------------|---------------|------|---------|
| I1 | CRITICAL | src/models/user.py (modifies) | 003-payment/T022 | File | Both modify User model |
| I2 | HIGH | ENT-Order (adds relationships) | 002-inventory/FR-004 | Entity | Inventory reads Order schema |
| ... | ... | ... | ... | ... | ... |

### Conflict Map

(Generate a Mermaid diagram showing the conflict relationships)

### Recommendations

- For each CRITICAL: Specific resolution guidance
- For each HIGH: Suggested coordination approach
- Overall: Whether it's safe to proceed to implementation
```

### 7. Update Feature Graph

If the current feature doesn't have a `dependency-graph.json` yet, create one from the footprint analysis in Step 3.

If it already exists, enrich it with any new nodes/edges discovered during analysis.

Write to `FEATURE_DIR/dependency-graph.json`.

### 8. Merge Into Global Index

Run the graph merge logic:
1. Re-merge all `specs/*/dependency-graph.json` into `.specify/graphs/index.json`
2. Validate graph integrity (no orphan node references in edges)

### 9. Provide Next Actions

- If CRITICAL conflicts found: "Resolve conflicts before running `/speckit.implement`. Consider `/speckit.depgraph.resolve` for structured resolution."
- If only HIGH: "Review conflicts with affected feature owners. You may proceed with caution."
- If only MEDIUM/LOW: "Safe to proceed. Consider these overlaps during implementation."
- If no conflicts: "No cross-feature conflicts detected. Safe to proceed."

## Guidelines

- Focus on **actionable** findings, not exhaustive reporting
- Limit findings to 50 items; summarize overflow
- Generate stable IDs (I1, I2, ...) for findings
- Mermaid conflict maps should focus on CRITICAL and HIGH items only
- Transitive impact analysis should respect the configured depth (default: 3 hops)
