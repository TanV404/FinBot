# FinBot Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-16

## Active Technologies

- (001-realtime-data-ingestion)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

# Add commands for 

## Code Style

: Follow standard conventions

## Recent Changes

- 001-realtime-data-ingestion: Added

## Napkin - Persistent Memory

You maintain a per-repo file at `.specify/memory/napkin.md` that tracks mistakes,
corrections, and patterns. **This behavior is always active.**

**Session Start**: Read `.specify/memory/napkin.md` before doing anything else.
If it does not exist, create it from `.specify/templates/napkin-entry-template.md`.
Apply what you learn silently.

**During Work**: Update the napkin whenever you learn something worth recording:
- Your own mistakes (wrong assumptions, failed approaches, misread code)
- User corrections (anything the user told you to do differently)
- Tool/environment surprises (unexpected repo behavior)
- Preferences (how the user likes things done)
- What worked (successful approaches worth repeating)

Use structured entries with: Category, Context, What Went Wrong, What Fixed It,
Lesson Learned, Impact, Prevention, Tags, and Distillation Status.

Be specific. "Made an error" is useless. "Assumed the API returns a list but
it returns a paginated object with .items" is actionable.

**Maintenance**: Every 5-10 sessions, consolidate: merge redundant entries,
promote repeated corrections, remove outdated notes. Keep under ~200 lines.

## Handovers - Session Context Preservation

Session handovers prevent context loss between sessions.

**Before ending incomplete work**: Create a handover at
`.specify/memory/handovers/YYYY-MM-DD_session-NNN.md` capturing accomplishments,
decisions, pitfalls, lessons, next TODOs, and open questions. Update
`.specify/memory/handovers/latest.md` to point to the new handover.

**When resuming work**: Read `.specify/memory/handovers/latest.md` first.
Apply the context, check branch alignment, and continue from where the
previous session left off.

## Project Context - Auto-Update

If you add/update dependencies, update the "Active Technologies" section above.
If you change project structure, update the "Project Structure" section above.
Perform these updates even when refactoring or fixing bugs, if the context changes.

## Dependency Graph Awareness

If `.specify/graphs/index.json` exists, you are working in a graph-aware project.

**Session Start**: After reading napkin, check `.specify/graphs/index.json` for the current
feature's nodes. Note any cross-feature dependencies or recent conflicts. If conflict
resolution annotations exist on edges, respect the decided strategies.

**During Implementation**: When modifying files, check if they appear as nodes in other
features' graphs. If so, flag potential impact before making changes. Prefer smaller,
backward-compatible changes to shared components.

**Before Ending Session**: If you created or modified files not in the graph, note them
in the handover for graph enrichment in the next session. Consider running
`/speckit.depgraph.impact` to update the graph.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
