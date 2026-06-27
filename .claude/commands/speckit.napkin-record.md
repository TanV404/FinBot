---
description: Record a mistake or lesson learned in the napkin for future reference
handoffs:
  - label: Review Napkin Patterns
    agent: speckit.napkin-review
    prompt: Analyze napkin for recurring patterns
  - label: Resume Work
    agent: speckit.resume
    prompt: Resume from latest handover
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This workflow helps record mistakes, bugs, corrections, and lessons learned in `.specify/memory/napkin.md` to enable continuous improvement.

1. **Check napkin.md exists**:
   - If `.specify/memory/napkin.md` doesn't exist, create it with the standard header from `.specify/templates/napkin-entry-template.md`
   - If it exists, load it to understand existing entries

2. **Gather information from user** (if not provided in arguments):

   Ask the user to provide:

   **Category** (required): What type of issue was this?
   - SPEC: Specification ambiguity or oversight
   - PLAN: Planning or architectural mistake
   - IMPLEMENTATION: Code bug or implementation error
   - TEST: Test failure or testing oversight
   - CONSTITUTION: Constitutional principle violation
   - ARCHITECTURE: Design pattern or structure issue
   - PERFORMANCE: Performance or optimization issue

   **Context** (required):
   - Feature name and branch (if applicable)
   - File(s) affected
   - Component or module affected

   **What Went Wrong** (required):
   - Detailed description of the problem
   - When was it discovered?
   - What were the symptoms?

   **What Fixed It** (required):
   - The solution, workaround, or correction
   - Include code snippets if relevant

   **Lesson Learned** (required):
   - Generalized principle for future application
   - Must be actionable and clear

   **Impact** (optional but recommended):
   - Time lost (estimate: minutes/hours/days)
   - Severity: LOW | MEDIUM | HIGH | CRITICAL
   - Likelihood of recurrence: LOW | MEDIUM | HIGH

   **Prevention** (recommended):
   - How to prevent this in the future?
   - Should this become a workflow step? Constitution principle? Checklist item?

3. **Format the entry** using the napkin entry template structure:

   ```markdown
   ## [YYYY-MM-DD HH:MM] | [CATEGORY] | [Short Title]

   **Category**: [CATEGORY]

   **Context**:
   - Feature: [Feature name]
   - File(s): [Files]
   - Component: [Component]

   **What Went Wrong**:
   [Description]

   **What Fixed It**:
   [Solution]

   **Lesson Learned**:
   [Generalized principle]

   **Impact**:
   - Time Lost: [Estimate]
   - Severity: [LEVEL]
   - Likelihood of Recurrence: [LEVEL]

   **Prevention**:
   [Prevention strategy]

   **References**:
   - Commit: [if applicable]
   - Handover: [if applicable]
   - Related Napkin Entries: [if applicable]

   **Tags**: #[tag1] #[tag2] #[tag3]

   **Distillation Status**: [ ] Not reviewed | [ ] Reviewed | [ ] Constitutionalized
   ```

4. **Append to napkin.md**:
   - Add the new entry to the "## Entries" section
   - Keep entries in reverse chronological order (newest first)
   - Preserve all existing content

5. **Check for patterns**:
   - Search napkin.md for similar issues (by category or tags)
   - If this is the 3rd+ occurrence of a similar pattern, flag it:
     - **WARNING**: "This is the [N]th time we've encountered [pattern]. Consider running `/speckit.napkin-review` to distill this into a constitution principle."

6. **Suggest constitution amendment** (if applicable):
   - If severity is CRITICAL and likelihood of recurrence is MEDIUM or HIGH
   - If this is a recurring pattern (3+ similar entries)
   - Suggest: "Consider running `/speckit.napkin-distill` to elevate this lesson to a constitutional principle."

7. **Report completion**:
   - Confirm entry was recorded
   - Display the formatted entry
   - Show total napkin entries count
   - Suggest next steps if patterns detected

## Guidelines

- **Be honest**: Record failures and mistakes openly
- **Be specific**: Include file paths, line numbers, exact errors
- **Extract the lesson**: Don't just describe -- generalize the principle
- **Tag appropriately**: Use tags for technology, feature area, type of issue
- **Link context**: Reference commits, handovers, related entries

## Notes

- This workflow can be run interactively (ask questions) or batch mode (if user provides all info in arguments)
- Always preserve existing napkin.md content
- Use current timestamp in ISO format
- Encourage specificity over vagueness
