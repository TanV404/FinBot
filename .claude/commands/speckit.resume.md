---
description: Resume work from a previous session using the latest handover document
handoffs:
  - label: Create New Handover
    agent: speckit.handover
    prompt: Create a session handover before ending work
  - label: Start New Feature
    agent: speckit.specify
    prompt: Create a new feature specification
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This workflow loads the most recent handover document to restore context from a previous session, preventing "amnesia" and preserving continuity.

1. **Locate latest handover**:
   - Check `.specify/memory/handovers/latest.md` exists
   - If not found, check `.specify/memory/handovers/` for any handover files
   - If no handovers exist: "No handovers found. This appears to be a fresh start. Use `/speckit.specify` to begin a new feature or `/speckit.handover` to create your first handover."
   - If multiple exist but no latest.md, use most recent by filename (YYYY-MM-DD_session-NNN.md)

2. **Load handover context**:
   - Read the latest handover file
   - Parse key sections:
     - Session Goal
     - What We Accomplished
     - Key Decisions Made
     - Pitfalls Encountered
     - Lessons Learned
     - Next Session TODO
     - Open Questions
     - For Next Session's Agent section

3. **Display session summary**:

   Present a clear, scannable summary to user:

   ```markdown
   # Resuming Session: [Feature Name]

   **Last Session**: [Date and time]
   **Session Duration**: [X hours]
   **Feature Branch**: [branch-name]
   **Status**: [In Progress | Blocked | ...]

   ---

   ## Last Session Summary

   **Goal**: [What they were trying to accomplish]

   **Accomplished**:
   - [Key accomplishment 1]
   - [Key accomplishment 2]

   **Progress**: [X]% complete ([Y] of [Z] tasks)

   ---

   ## Key Decisions (Refresher)

   [List 1-3 most important decisions with brief rationale]

   ---

   ## Watch Out For

   [List gotchas, pitfalls, or warnings from "For Next Session's Agent" section]

   ---

   ## Lessons From Last Session

   [Top 2-3 lessons learned]

   ---

   ## Next Steps (Priority Order)

   **High Priority**:
   - [ ] [Task 1]
   - [ ] [Task 2]

   **Medium Priority**:
   - [ ] [Task 3]

   **Suggested First Action**: [Quick win or logical next step]

   ---

   ## Open Questions

   [List unresolved questions that need decisions]
   ```

4. **Check current state alignment**:

   - Run `git branch --show-current`
   - Compare to handover's feature branch
   - If different: **WARNING**: "Handover is for branch `[X]` but you're on `[Y]`. Switch branches? (yes/no)"
   - Run `git status` to check for uncommitted changes
   - If dirty working tree: **CAUTION**: "You have uncommitted changes. Stash them before switching branches?"

5. **Load related documents**:

   - Read spec.md, plan.md, tasks.md from handover links
   - Cross-reference tasks.md status with handover TODO list
   - Check if tasks.md was updated since handover (git log)

6. **Check for new napkin entries**:

   - Read napkin.md
   - Filter for entries created AFTER last handover date
   - If any exist: "FYI: There are [N] new napkin entries since this handover was created. Relevant lessons: [list]"

7. **Present action menu**:

   Ask user how they want to proceed:

   ```
   How would you like to proceed?

   1. **Continue from last session** - Pick up where we left off
   2. **Modify approach** - Change direction or priorities
   3. **Review handover details** - Read full handover first
   4. **Switch to different feature** - Work on something else
   5. **Create new handover** - Update context from previous session

   Your choice: [1-5]
   ```

8. **Execute user choice**:

   **Choice 1 (Continue)**:
   - Load the suggested next command from handover
   - Ask: "Ready to continue with implementation?"
   - If yes, proceed with the workflow

   **Choice 2 (Modify)**:
   - Ask what changed
   - Update tasks.md if needed
   - Suggest creating new handover to record the change in approach

   **Choice 3 (Review)**:
   - Display full handover document
   - Then re-present action menu

   **Choice 4 (Switch)**:
   - Ask which feature branch
   - Optional: Create handover for current work before switching
   - Check out new branch
   - Look for handover for that feature

   **Choice 5 (New Handover)**:
   - Run `/speckit.handover` workflow

## Edge Cases

**No Latest Handover**:
- If latest.md missing but other handovers exist, use most recent
- List available handovers and ask user to choose

**Stale Handover** (>7 days old):
- Warning: "This handover is [N] days old. Consider creating a new one before continuing to ensure current context is captured."

**Conflicting State**:
- If branches don't match: offer to switch
- If tasks.md diverged: offer to sync
- If uncommitted changes: offer to stash

**Multiple Features**:
- If user has multiple active branches with handovers, list them
- Ask which one to resume

## Guidelines

- Make it easy to "pick up where you left off"
- Surface the most important context first (summary, warnings, next steps)
- Full details available but don't overwhelm initially
- Always check alignment (branch, files, status)
- Smooth transition into next workflow (implement, plan, etc.)

## Notes

- This workflow is ideally run at the START of every session on an existing feature
- Reading latest.md should be FAST
- The goal is seamless continuity, not re-reading everything
- Trust the handover -- it was created deliberately by the previous session
