---
description: Distill napkin patterns into constitution amendments with approval workflow
handoffs:
  - label: Review Napkin Patterns
    agent: speckit.napkin-review
    prompt: Analyze napkin for recurring patterns first
  - label: View Constitution
    agent: speckit.constitution
    prompt: Review the current constitution
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This workflow extracts high-level principles from napkin.md patterns and elevates them to constitutional amendments with user approval.

**Prerequisites**: Should be run after `/speckit.napkin-review` identifies constitution amendment candidates.

1. **Load context**:
   - Read `.specify/memory/napkin.md`
   - Read `.specify/memory/constitution.md` to understand current principles
   - Check for recent napkin analysis reports in `.specify/memory/napkin-analysis-*.md`
   - If no analysis report exists, run pattern detection (abbreviated version of `/speckit.napkin-review`)

2. **Identify amendment candidates**:

   Use these criteria:
   - **Recurring Pattern**: 3+ napkin entries with same root cause
   - **High Impact**: CRITICAL severity OR >4 hours time lost OR HIGH recurrence likelihood
   - **Prevention Suggestion**: Napkin entry suggests process/workflow change
   - **Not Already in Constitution**: Lesson isn't covered by existing principles

   For each candidate:
   - Extract the core lesson
   - Identify supporting napkin entries
   - Draft proposed constitutional text
   - Determine principle type (new principle vs. amendment to existing)

3. **Draft constitutional amendments**:

   For each amendment candidate, create:

   ```markdown
   ## Proposed Amendment [N]: [Principle Name]

   **Type**: [New Principle | Amendment to Principle [Roman Numeral] | New Development Practice]

   **Evidence** ([N] napkin entries):
   - [Entry date + title]: [Brief description of issue]

   **Problem Statement**:
   [What keeps going wrong? Why is this a pattern?]

   **Proposed Constitutional Text**:

   ### [Principle Number/Name]

   [Draft constitutional text in same style as existing principles]

   **Impact**:
   - **Prevents**: [What this stops from happening]
   - **Requires**: [What changes to workflows/templates]
   - **Affects**: [Which workflows/templates need updates]

   **Enforcement**:
   - [How this principle will be checked/validated]
   - [Which workflow step enforces this]

   **Related Principles**:
   - [Existing principles this complements or modifies]

   **Implementation Checklist**:
   - [ ] Update constitution.md
   - [ ] Update affected workflows
   - [ ] Update affected templates
   - [ ] Update checklists
   - [ ] Mark napkin entries as "Constitutionalized"
   ```

4. **Present amendments to user for approval**:

   Display each proposed amendment clearly:
   - Show evidence (napkin entries)
   - Show proposed constitutional text
   - Show impact and required changes
   - Ask for approval: "Approve this amendment? (yes/no/modify)"

   User options:
   - **Yes**: Approve as-is
   - **No**: Skip this amendment
   - **Modify**: User provides revised text (update draft and ask for approval again)

5. **For each approved amendment**:

   a. **Determine version bump**:
   - MAJOR: If removing/redefining existing principle (ask user to confirm)
   - MINOR: If adding new principle or materially expanding existing one
   - PATCH: If minor clarification only

   b. **Update constitution.md**:
   - If new principle: Add to "## Core Principles" section in appropriate order
   - If amendment: Modify existing principle text
   - If development practice: Add to "## Development Practices" section
   - Update version number according to semantic versioning
   - Update "Last Amended" date

   c. **Mark napkin entries as constitutionalized**:
   - Find all napkin entries that contributed to this amendment
   - Update their "Distillation Status" to: `[x] Constitutionalized`
   - Add reference to constitution version where they were incorporated

6. **Update affected artifacts**:

   For each approved amendment, check which files need updates:
   - Workflow command templates - Add checks for new principles
   - Templates - Add validation steps
   - Existing feature specs, plans, tasks - May need retroactive review

   Generate update checklist and report to user.

7. **Generate amendment summary**:

   ```markdown
   # Constitution Amendment Summary

   **Date**: [YYYY-MM-DD]
   **Version**: [Old] -> [New]
   **Amendments Applied**: [N]

   ---

   ## Approved Amendments

   ### Amendment 1: [Principle Name]
   - **Type**: [New Principle | Amendment | Practice]
   - **Based on**: [N] napkin entries
   - **Impact**: [Summary]
   - **Files Updated**: [List]

   ---

   ## Required Follow-up Actions

   - [ ] Update workflow: [name]
   - [ ] Update template: [name]
   - [ ] Commit constitution changes

   ---

   ## Napkin Entries Constitutionalized

   [List of napkin entries marked as constitutionalized with dates]
   ```

8. **Save amendment record**:
   - Save summary to `.specify/memory/constitution-amendment-[YYYY-MM-DD].md`
   - Update constitution.md
   - Report completion with file paths

## Guidelines

- Only distill patterns with strong evidence (3+ entries or CRITICAL severity)
- Constitutional text should match existing style and tone
- Be specific about enforcement mechanisms
- Don't create vague principles -- they must be testable/verifiable
- Always get user approval before modifying constitution
- Update all related documents atomically

## Notes

- This is a significant workflow -- constitutionalizing lessons is a deliberate act
- Should be run thoughtfully, not automatically
- User approval is REQUIRED for each amendment
- Constitution version must be bumped according to semantic versioning
- All affected workflows/templates must be flagged for update
