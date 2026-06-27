---
description: "Verify that implementation matches the feature specification, detecting spec drift and coverage gaps post-implementation"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

After implementation is complete (or partially complete), compare the original specification against the actual code to detect drift, missing implementations, and divergence from the plan. This closes the feedback loop between specification and implementation.

## Operating Constraints

- **Read-only on source code**: Read all source files but do not modify them.
- **May update graph**: If `dependency-graph.json` exists, may add staleness annotations.
- **Runs post-implementation**: Designed to run after `/speckit.implement` completes, but can run at any point during implementation for progress checking.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries about spec drift, implementation divergence, or verification issues
- Apply lessons to focus verification on historically problematic areas

### 1. Initialize Context

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS.

Required files: `spec.md`, `plan.md`, `tasks.md`
Optional files: `data-model.md`, `contracts/`, `dependency-graph.json`, `monitoring.md`

### 2. Build Verification Model

From the feature artifacts, build a verification checklist:

**From spec.md**:
- Extract all functional requirements (FR-xxx)
- Extract acceptance scenarios (Given/When/Then)
- Extract success criteria
- Extract key entities

**From plan.md**:
- Extract planned file structure
- Extract data model entities and fields
- Extract API endpoint definitions from contracts/

**From tasks.md**:
- Extract all tasks and their file paths
- Note which tasks are marked complete ([x]) vs incomplete ([ ])

**From dependency-graph.json** (if exists):
- Extract all file nodes → verify files exist on disk
- Extract entity nodes → verify entities match actual code
- Extract endpoint nodes → verify endpoints exist in code

### 3. Verify Requirements Coverage

For each functional requirement (FR-xxx):

1. **Find implementation**: Search the codebase for code that implements this requirement
   - Use file paths from tasks and graph nodes as hints
   - Look for comments, function names, or logic matching the requirement
2. **Assess coverage**:
   - **Fully Implemented**: Clear code path covers the requirement
   - **Partially Implemented**: Some aspects present, others missing
   - **Not Implemented**: No evidence of implementation
   - **Divergent**: Implemented differently than specified

### 4. Verify File Structure

Compare the planned project structure (from plan.md) against actual files:
- Files planned but not created
- Files created but not planned (unspecified additions)
- Files that exist but are empty or stubs

### 5. Verify Data Model

If data-model.md exists, compare against actual model definitions:
- Entities defined but not implemented
- Fields missing from implementations
- Relationships not reflected in code
- Extra fields/entities not in the data model

### 6. Verify API Contracts

If contracts/ directory exists, compare against actual endpoint implementations:
- Endpoints defined but not implemented
- Response schemas that don't match contract definitions
- Missing error handling for specified failure modes

### 7. Verify Graph Integrity (if dependency-graph.json exists)

- Check all file nodes reference files that still exist
- Check all entity nodes match actual code entities
- Verify edge relationships still hold (imports, dependencies)
- Flag stale nodes where the underlying code has changed significantly

### 8. Produce Spec Drift Report

```markdown
## Spec Drift Report

**Feature**: [feature name]
**Verification Date**: [timestamp]
**Implementation Status**: [Complete / In Progress / Stalled]

### Summary

| Metric | Count |
|--------|-------|
| Requirements Verified | [N] of [M] |
| Fully Implemented | [N] |
| Partially Implemented | [N] |
| Not Implemented | [N] |
| Divergent | [N] |
| Planned Files Created | [N] of [M] |
| Tasks Completed | [N] of [M] |

### Requirement Coverage

| Req ID | Status | Evidence | Notes |
|--------|--------|----------|-------|
| FR-001 | Fully Implemented | src/services/user_service.py:L23-45 | Matches spec |
| FR-002 | Divergent | src/models/user.py:L12 | Uses email instead of username |
| FR-003 | Not Implemented | — | No code found |

### File Structure Drift

| Category | Files |
|----------|-------|
| Planned & Created | [list] |
| Planned but Missing | [list] |
| Unplanned Additions | [list] |

### Data Model Drift (if applicable)

| Entity | Status | Drift Details |
|--------|--------|---------------|
| User | Partial | Missing 'phone_number' field from spec |

### Graph Staleness (if dependency-graph.json exists)

| Node | Status | Details |
|------|--------|---------|
| FILE-src/old-module.py | Stale | File deleted |
| ENT-Order | Drifted | 3 new fields not in graph |

### Severity Summary

- **CRITICAL**: [N] requirements not implemented
- **HIGH**: [N] requirements divergent from spec
- **MEDIUM**: [N] partially implemented requirements
- **LOW**: [N] file structure differences
```

### 9. Provide Recommendations

Based on drift severity:
- **If CRITICAL drift**: "Update implementation to cover missing requirements, or update spec to reflect intentional scope changes"
- **If HIGH drift**: "Review divergent implementations — update spec or code to align"
- **If only MEDIUM/LOW**: "Implementation substantially matches spec. Consider updating spec to document intentional changes."
- **Record in napkin**: Suggest recording significant drift patterns as napkin entries

## Guidelines

- Be thorough but practical — small cosmetic differences are LOW severity
- Use file content analysis, not just file existence checks
- Cross-reference tasks.md completion status with actual code presence
- If the spec has been updated since implementation started, note the version discrepancy
- This command is safe to run multiple times during implementation for progress checks
