---
description: Analyze napkin.md for patterns and suggest constitution amendments
handoffs:
  - label: Distill Patterns to Constitution
    agent: speckit.napkin-distill
    prompt: Elevate recurring patterns to constitution amendments
  - label: Record New Lesson
    agent: speckit.napkin-record
    prompt: Record a new lesson in the napkin
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This workflow analyzes `.specify/memory/napkin.md` to identify recurring patterns, common pitfalls, and lessons that should be elevated to constitutional principles.

1. **Load napkin.md**:
   - Read `.specify/memory/napkin.md`
   - If file doesn't exist or is empty, report: "No napkin entries found. Use `/speckit.napkin-record` to record your first lesson."
   - Count total entries

2. **Parse and categorize**:
   - Group entries by category (SPEC, PLAN, IMPLEMENTATION, TEST, CONSTITUTION, ARCHITECTURE, PERFORMANCE)
   - Group entries by tags
   - Group entries by severity (CRITICAL, HIGH, MEDIUM, LOW)
   - Identify entries with high recurrence likelihood

3. **Pattern detection**:

   For each category and tag combination, look for:

   **Recurring Issues** (3+ similar entries):
   - Extract common themes from "What Went Wrong"
   - Identify if same root cause appears multiple times

   **High-Impact Lessons** (CRITICAL severity or HIGH recurrence likelihood):
   - Lessons that caused significant time loss
   - Issues that could cause production bugs
   - Security or data integrity concerns

   **Prevention Opportunities**:
   - Look at "Prevention" sections across entries
   - Identify suggestions for workflow changes, checklist items, or constitution principles
   - Group by implementation feasibility

4. **Generate pattern report**:

   Create a structured analysis:

   ```markdown
   # Napkin Pattern Analysis Report

   **Generated**: [Timestamp]
   **Total Entries**: [N]
   **Analysis Period**: [Date range of entries]

   ---

   ## Summary Statistics

   | Category | Count | Avg Severity | Avg Time Lost |
   |----------|-------|--------------|---------------|
   | IMPLEMENTATION | [N] | [Level] | [Time] |
   | SPEC | [N] | [Level] | [Time] |
   | ... | ... | ... | ... |

   **Total Time Lost**: [Sum across all entries]

   ---

   ## Recurring Patterns

   ### Pattern 1: [Pattern Name]
   - **Frequency**: [N] occurrences
   - **Categories**: [List]
   - **Common Root Cause**: [Description]
   - **Example Entries**: [Links to napkin entries]
   - **Recommended Action**: [What should be done]

   ---

   ## High-Impact Issues

   [List of CRITICAL severity or HIGH recurrence entries]

   ---

   ## Constitution Amendment Candidates

   [Lessons that should become constitutional principles]

   ### Candidate 1: [Proposed Principle Name]
   - **Based on**: [N] napkin entries
   - **Problem**: [What keeps going wrong]
   - **Proposed Principle**: [Draft constitutional text]
   - **Impact**: [What this would prevent]

   ---

   ## Workflow Integration Opportunities

   [Suggestions for updating workflows, templates, or checklists based on lessons]

   ---

   ## Recommendations

   **Immediate Actions**:
   1. [High-priority recommendation]

   **Long-term Improvements**:
   1. [Strategic recommendation]

   **Next Steps**:
   - Run `/speckit.napkin-distill` to elevate [N] patterns to constitution
   ```

5. **Highlight constitution candidates**:

   For each potential constitutional principle:
   - Show the pattern evidence (napkin entries)
   - Draft the constitutional text
   - Explain the impact and enforcement mechanism
   - Suggest which existing principle it relates to (or if it's net new)

6. **Update napkin.md Pattern Analysis section**:

   - Update the "## Pattern Analysis" section in napkin.md
   - Add identified patterns
   - Mark constitution amendment candidates
   - Update timestamp

7. **Generate actionable output**:

   Present to user:
   - Summary statistics
   - Top 3 recurring patterns
   - Constitution amendment candidates (if any)
   - Recommended next actions

   If constitution amendments recommended:
   - Ask: "Would you like me to run `/speckit.napkin-distill` to create constitutional amendments for these [N] patterns?"

8. **Save the report**:

   - Save full report to `.specify/memory/napkin-analysis-[YYYY-MM-DD].md`
   - Report file path to user
   - Update napkin.md with link to report

## Pattern Detection Heuristics

**Recurring Pattern** (trigger rule):
- 3+ entries with same category + similar root cause
- OR 2+ entries with CRITICAL severity + same root cause

**Constitution Candidate** (trigger rule):
- Pattern is recurring (as defined above)
- AND (Severity is CRITICAL OR Likelihood of Recurrence is HIGH)
- AND Prevention suggests workflow/process change

**High-Impact Issue**:
- Severity = CRITICAL
- OR Time Lost > 4 hours
- OR Likelihood of Recurrence = HIGH with Severity >= MEDIUM

## Notes

- This workflow should be run periodically (e.g., every 5-10 napkin entries)
- Can be run on-demand when user suspects a pattern
- Report files are saved for historical reference
- Focus on actionable recommendations, not just statistics
