---
description: "Conduct a structured review of the feature specification, tracking review status and feedback"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Facilitate a structured review of the feature specification before proceeding to planning. Evaluates the spec across multiple quality dimensions, records reviewer feedback, and tracks review status. Optionally gates `/speckit.plan` on review approval.

## Operating Constraints

- **Modifies spec.md only**: Updates the Review Status field and adds Review Notes section.
- **Interactive**: Guides the reviewer through a structured evaluation.
- **Graph-enhanced**: If dependency graph exists, annotates the review with cross-feature impact context.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries about specification quality, review lessons, or missed requirements
- Apply lessons to focus review on historically problematic areas

### 1. Initialize Context

Run `.specify/scripts/bash/check-prerequisites.sh --json --paths-only` from repo root and parse JSON for FEATURE_SPEC and FEATURE_DIR.

If FEATURE_SPEC doesn't exist: error — "No spec found. Run `/speckit.specify` first."

### 2. Load Spec and Context

- Read `FEATURE_SPEC` fully
- If `.specify/graphs/index.json` exists:
  - Check what existing features share components with this spec's entities/files
  - Prepare cross-feature impact annotation
- If `.specify/memory/constitution.md` exists:
  - Load principles for constitution alignment check

### 3. Present Cross-Feature Context (if graph available)

If the dependency graph reveals overlap with existing features:

```markdown
## Cross-Feature Impact Context

This specification touches components shared by other features:

| Component | Other Features | Overlap Type |
|-----------|---------------|-------------|
| User entity | 001-auth, 003-payment | Schema dependency |
| /api/orders endpoint | 002-inventory | Endpoint shared |

**Risk Level**: [Low/Medium/High] based on overlap density
```

### 4. Structured Review Framework

Guide the reviewer through each dimension. For each, assess and record:

**A. Completeness** (Are all required sections filled out?)
- All mandatory sections present and populated
- No placeholder text remaining
- Edge cases identified
- Key entities defined

**B. Clarity** (Are requirements unambiguous?)
- No vague adjectives without metrics ("fast", "scalable", "intuitive")
- Acceptance scenarios are specific and testable
- Terminology is consistent throughout

**C. Feasibility** (Can this reasonably be built?)
- Scope is achievable within expected timeline
- No requirements that contradict each other
- Dependencies are identified and available

**D. Risk Assessment**
- Security implications identified
- Performance requirements are realistic
- External dependencies have fallback strategies
- Cross-feature conflicts flagged (from graph)

**E. Constitution Alignment**
- All MUST principles respected
- No violations of core project standards
- Quality gates are satisfiable

For each dimension, record:
- **Status**: Pass / Concern / Fail
- **Notes**: Specific observations
- **Suggestions**: Recommended changes

### 5. Record Review

Update `FEATURE_SPEC`:

1. **Update Review Status** in the spec header:
   - Change `**Review Status**: Draft` to `**Review Status**: In Review` (first review)
   - Or to `**Review Status**: Approved` (if all dimensions pass)

2. **Add Review Notes section** (if not already present):

```markdown
## Review Notes

### Review Session [DATE]

**Reviewer**: [user/agent]
**Overall**: [Approved / Changes Requested / Blocked]

| Dimension | Status | Notes |
|-----------|--------|-------|
| Completeness | Pass | All sections filled |
| Clarity | Concern | FR-003 uses "fast" without metric |
| Feasibility | Pass | Scope is reasonable |
| Risk | Concern | No security considerations for PII |
| Constitution | Pass | Aligned with all principles |

**Action Items**:
1. Quantify "fast" in FR-003 with specific latency target
2. Add PII handling requirements for user data
```

### 6. Determine Review Outcome

Based on dimension assessments:

- **Approved**: All dimensions Pass → set status to "Approved", proceed to `/speckit.plan`
- **Changes Requested**: One or more Concerns → set status to "In Review", list required changes
- **Blocked**: Any Fail or constitution violation → set status to "Blocked", must resolve before planning

### 7. Report

Output:
- Review outcome (Approved / Changes Requested / Blocked)
- Summary of findings per dimension
- Action items for the spec author
- If Approved: "Spec is ready for `/speckit.plan`"
- If not: "Address action items and run `/speckit.review` again"

## Guidelines

- Be constructive, not pedantic — focus on issues that would cause downstream rework
- A Concern is not a blocker; it's a suggestion for improvement
- Only mark Fail for genuine quality gates (constitution violations, missing mandatory sections, contradictions)
- Multiple review sessions are expected — append to Review Notes, don't overwrite
- The review is of the **specification quality**, not the feature idea itself
