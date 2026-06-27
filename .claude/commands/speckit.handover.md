---
description: Generate a session handover document before ending work on a feature
handoffs:
  - label: Record Lesson in Napkin
    agent: speckit.napkin-record
    prompt: Record a lesson from this session
  - label: Resume Later
    agent: speckit.resume
    prompt: Resume work from latest handover
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This workflow creates a comprehensive handover document capturing the current session's context, decisions, and progress to preserve institutional knowledge between sessions.

1. **Detect current feature context**:
   - Run `git branch --show-current` to get current branch
   - If on a feature branch (matches pattern `[0-9]+-.*`), extract feature number and name
   - Look for corresponding spec directory in `specs/[number]-[name]/`
   - If not on a feature branch, ask user: "Which feature should this handover be for?"

2. **Gather session metrics**:
   - Current timestamp as session end time
   - Estimate session duration (ask user or check git log timestamps for rough estimate)
   - Load feature documents: spec.md, plan.md, tasks.md (if they exist)
   - Run `git status` and `git diff --stat` to see uncommitted changes
   - Run `git log --since="12 hours ago" --oneline` to see recent commits

3. **Generate handover file name**:
   - Format: `YYYY-MM-DD_session-NNN.md`
   - Check `.specify/memory/handovers/` for existing sessions today
   - Increment session number if multiple sessions in same day

4. **Populate handover using template**:

   Load `.specify/templates/handover-template.md` and fill in:

   **Session Goal**: Ask user "What was your main goal for this session?"

   **Accomplishments**:
   - Parse tasks.md to find recently completed tasks (marked with [x])
   - List files modified (from git status/diff)
   - Ask user: "What did you accomplish? (I detected [N] tasks complete and [M] files modified)"

   **Key Decisions**:
   - Ask user: "Were any important decisions made this session?"
   - For each decision, capture: context, choice, rationale, alternatives, impact

   **Pitfalls Encountered**:
   - Check if any recent napkin entries exist from today
   - Ask user: "Did you encounter any problems or bugs?"
   - For each pitfall: problem, impact, resolution, time lost
   - Suggest recording in napkin if not already done

   **Lessons Learned**:
   - Extract from pitfalls
   - Ask user: "Any key insights or wisdom from this session?"
   - Flag high-value lessons for napkin.md

   **Next Session TODO**:
   - Parse tasks.md for incomplete tasks (marked with [ ] or [/])
   - Prioritize based on dependencies and user input
   - Ask user: "What should be the top priority for the next session?"

   **Key Files Modified**:
   - Generate table from git diff --stat
   - Include file paths, change description, line counts, status

   **Open Questions**:
   - Ask user: "Are there any unresolved questions or decisions deferred for later?"

   **Effort Tracking**:
   - Parse tasks.md for completed tasks with [Est:N] markers
   - Sum estimated points completed vs. remaining
   - Calculate velocity: points completed / session duration (approximate)
   - Ask user: "How long was this session approximately? (e.g., 2 hours)"
   - If user provides actual time per task, track actual vs. estimated

   **Testing Status**:
   - If tests/ directory exists, estimate test coverage
   - Ask user about test results

   **Related Context**:
   - Auto-link to spec.md, plan.md, tasks.md
   - Link to previous handover if exists
   - Link to constitution
   - Link to relevant napkin entries from today

   **For Next Session's Agent**:
   - Auto-generate TL;DR based on status
   - Ask user for critical context or gotchas
   - Suggest quick wins from incomplete tasks

5. **Write handover file**:
   - Save to `.specify/memory/handovers/[filename]`
   - Ensure all markdown formatting is clean

6. **Update handover index**:
   - Read `.specify/memory/handovers/index.md`
   - Add new entry to "## All Handovers" section
   - Update statistics (total handovers, active sessions)
   - Update "Last Handover Created" timestamp
   - Write back to index.md

7. **Create/update latest.md**:
   - Copy handover content to `.specify/memory/handovers/latest.md`
   - This file is always the most recent handover (for easy access)

8. **Record handover creation in napkin** (meta-entry):
   - Add a brief entry to napkin.md noting handover was created
   - Links back to handover file

9. **Report completion**:
   ```
   Session Handover Created

   **File**: .specify/memory/handovers/[filename]
   **Feature**: [branch-name]
   **Session Duration**: [X hours]
   **Status**: [In Progress | Blocked | Ready for Testing]

   **Quick Summary**:
   - Accomplished: [N] tasks, [M] files modified
   - Decisions: [N] key decisions recorded
   - Pitfalls: [N] issues encountered
   - Next Priority: [Top task for next session]

   **To Resume**: Run `/speckit.resume` at the start of your next session
   ```

## Interactive Prompts

This workflow should be conversational. Ask questions rather than assuming. Auto-detect what you can (tasks, files, commits) but ask for context. Encourage specificity. Link everything -- specs, plans, tasks, napkin entries, commits. Make it easy to resume -- prioritized TODO list is critical. Capture decisions AND rationale -- future sessions need to know WHY.

## Guidelines

- Quality over speed -- thorough handovers save hours later
- Should take 5-10 minutes of user interaction
- Handover files are markdown and can be committed to git for team sharing
- This workflow is run manually by user before ending session

## Notes

- This is a manual workflow run before ending a session
- Always preserve existing handover files (never overwrite)
- latest.md is the only file that gets overwritten (always most recent)
