---
description: "Resolve identified dependency graph conflicts with a structured workflow"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Provide a structured workflow for resolving conflicts identified by `/speckit.depgraph.impact`. For each CRITICAL or HIGH conflict, guide the user through resolution options, record the decision in the graph, and update the napkin for future learning.

## Operating Constraints

- **Interactive**: This command requires user input for each resolution decision.
- **Graph-mutating**: Updates `dependency-graph.json` and `.specify/graphs/index.json` with resolution annotations.
- **Napkin-writing**: Records lessons learned from conflict resolution.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for past conflict resolution entries
- Note patterns: recurring conflicts, preferred resolution strategies, common pitfalls

### 1. Load Conflict Data

Determine conflict source:

- If `$ARGUMENTS` references a specific impact report or finding IDs (e.g., `I1 I3 I5`): load those specific findings
- If no arguments: run `/speckit.depgraph.impact` internally to get fresh conflict data
- If `.specify/graphs/index.json` doesn't exist: error — run discovery or impact first

Filter to CRITICAL and HIGH conflicts only (MEDIUM/LOW are informational and don't require resolution).

### 2. Present Conflicts for Resolution

For each conflict, present a structured resolution prompt:

```markdown
## Conflict [ID]: [Brief description]

**Severity**: [CRITICAL/HIGH]
**This Feature**: [component/file/entity] — [what it does]
**Conflicts With**: [other feature] / [component] — [what it does]
**Type**: [File overlap / Entity schema change / API conflict / Requirement contradiction]

**Context**:
[Brief explanation of why this is a conflict and what could go wrong if unresolved]

### Resolution Options

| Option | Strategy | Description | Trade-off |
|--------|----------|-------------|-----------|
| A | Coordinate | Both features proceed; align on shared contract/schema | Requires sync between teams; may delay both |
| B | Sequence | Feature [X] merges first; Feature [Y] adapts | Blocks one feature; cleaner integration |
| C | Abstract | Extract shared component into stable interface | Higher upfront effort; better long-term isolation |
| D | Defer | Flag for tech lead review; proceed with risk acknowledged | Fastest now; risk of merge conflicts later |

**Recommended**: [Option letter] — [Brief reasoning based on context and napkin patterns]

Your choice: [A/B/C/D or provide custom resolution]
```

### 3. Record Resolution

After the user selects a resolution for each conflict:

1. **Update the graph edge** with resolution metadata:

```json
{
  "from": "node-id-1",
  "to": "node-id-2",
  "relation": "conflicts-with",
  "metadata": {
    "severity": "CRITICAL",
    "resolution": {
      "strategy": "coordinate",
      "decision": "Both teams align on User model schema v2 before either merges",
      "decided_by": "user",
      "date": "YYYY-MM-DD"
    }
  }
}
```

2. **Write resolution to feature's `dependency-graph.json`**

3. **Merge back into `.specify/graphs/index.json`**

### 4. Record in Napkin

For each resolution, create a napkin entry:

```markdown
### [Date] Conflict Resolution: [Brief Title]

- **Category**: ARCHITECTURE
- **Context**: Feature [X] and Feature [Y] conflict on [component]
- **What Went Wrong**: [Description of the conflict]
- **What Fixed It**: Resolution strategy: [chosen strategy]. [Decision details]
- **Lesson Learned**: [Extracted lesson for future similar conflicts]
- **Impact**: [Time impact, coordination required]
- **Prevention**: [How to avoid this conflict pattern in the future]
- **Tags**: conflict-resolution, [feature-names], [component-type]
- **Distillation Status**: New
```

### 5. Generate Resolution Summary

After all conflicts are resolved, output a summary:

```markdown
## Conflict Resolution Summary

**Feature**: [current feature name]
**Date**: [today]
**Conflicts Resolved**: [N] of [M]

| ID | Severity | Conflict | Strategy | Decision |
|----|----------|----------|----------|----------|
| I1 | CRITICAL | User model overlap with 003-payment | Coordinate | Align on schema v2 |
| I3 | HIGH | Order entity extension vs 002-inventory | Sequence | 002 merges first |

### Action Items

1. [Specific follow-up actions from coordinate/sequence decisions]
2. [Team sync meetings needed]
3. [Shared interface definitions to create]

### Graph Updated

- [N] conflict edges annotated with resolutions
- Graph snapshot saved to `.specify/graphs/snapshots/YYYY-MM-DD_resolution.json`
- Napkin updated with [N] new entries

### Next Steps

- If all CRITICAL resolved: "Safe to proceed to `/speckit.implement`"
- If deferred items remain: "Review deferred items with tech lead before implementation"
```

### 6. Create Resolution Snapshot

Save a timestamped snapshot of the graph after resolution:
`.specify/graphs/snapshots/YYYY-MM-DD_resolution.json`

## Guidelines

- Always recommend a resolution option based on context and napkin history
- If napkin shows a pattern of similar conflicts, highlight it
- "Coordinate" is preferred when both features are in active development
- "Sequence" is preferred when one feature is closer to completion
- "Abstract" is preferred when the conflict is likely to recur across future features
- "Defer" should be the last resort — always explain the risk
- Record ALL resolutions, even deferred ones, for traceability
