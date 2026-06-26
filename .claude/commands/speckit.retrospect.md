---
description: "Conduct a structured postmortem or retrospective, tracing incidents through the dependency graph and feeding lessons back into napkin and constitution"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Provide a structured workflow for conducting postmortems (after incidents) or retrospectives (after feature completion). Traces affected components through the dependency graph if available, auto-generates napkin entries for lessons learned, and proposes constitution amendments for systemic issues.

## Operating Constraints

- **Interactive**: Gathers information from the user through structured prompts.
- **Writes to memory**: Creates retrospective reports, updates napkin, may propose constitution changes.
- **Graph-enhanced**: If dependency graph exists, uses it to trace blast radius and contributing factors.
- **Blameless**: Focus on systems and processes, not individuals.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries related to similar incidents or past retrospectives
- Note recurring patterns that might indicate systemic issues

### 1. Determine Retrospective Type

Ask the user or parse from `$ARGUMENTS`:

- **Incident Postmortem**: Something went wrong in production
- **Feature Retrospective**: Reflecting on a completed feature's development process
- **Process Retrospective**: Reviewing the SDD workflow effectiveness

### 2. Gather Context (Interactive)

**For Incident Postmortem**:
1. "What happened? Describe the incident in 1-2 sentences."
2. "When did it start and when was it resolved? (approximate timestamps)"
3. "What was the user/business impact? (e.g., N users affected, revenue lost, data corrupted)"
4. "What was the immediate fix?"
5. "Which component(s) or file(s) were involved?"

**For Feature Retrospective**:
1. "Which feature? (branch name or spec directory)"
2. "What went well during development?"
3. "What was harder than expected?"
4. "Were there any surprising dependencies or conflicts?"
5. "How accurate were the original estimates vs. actual effort?"

**For Process Retrospective**:
1. "What time period are we reviewing?"
2. "Which features were completed in this period?"
3. "What SDD steps felt most/least valuable?"
4. "Were there process bottlenecks?"

### 3. Trace Through Dependency Graph (if available)

If `.specify/graphs/index.json` exists:

**For Incident Postmortem**:
- Map the affected component(s) to graph nodes
- Trace all features that depend on the affected nodes → blast radius
- Identify the feature(s) that introduced the affected code → contributing context
- Check if any `conflicts-with` edges existed that were unresolved
- Check if any `threatens` edges (from threat modeling) predicted this scenario

**For Feature Retrospective**:
- Load the feature's `dependency-graph.json`
- Compare initial graph (from plan phase) against final graph (post-implement)
- Identify nodes/edges that were added during implementation but not planned
- Check for unresolved conflict edges

### 4. Analyze Root Cause

Based on gathered information and graph analysis:

**5 Whys Analysis**:
- Start with the incident/issue
- Ask "Why?" iteratively to reach root cause
- Present the chain to the user for validation

**Contributing Factors**:
- Process factors (was the SDD workflow followed?)
- Technical factors (architecture, dependencies, testing gaps)
- Communication factors (knowledge silos, handover issues)
- External factors (third-party changes, infrastructure issues)

### 5. Generate Retrospective Report

Write to `.specify/memory/retrospectives/YYYY-MM-DD_retro-NNN.md`:

```markdown
# [Incident Postmortem / Feature Retrospective]: [Title]

**Date**: [today]
**Type**: [Incident Postmortem / Feature Retrospective / Process Retrospective]
**Participants**: [user / team]

## Summary

[1-2 sentence summary]

## Timeline (for incidents)

| Time | Event |
|------|-------|
| [timestamp] | [what happened] |

## Impact

- **Users Affected**: [count/description]
- **Duration**: [time]
- **Severity**: [P1/P2/P3]
- **Features in Blast Radius** (from graph): [list]

## Root Cause Analysis

### 5 Whys

1. Why: [first level]
2. Why: [second level]
3. Why: [third level]
4. Why: [fourth level]
5. Why: [root cause]

### Contributing Factors

| Factor | Type | Description |
|--------|------|-------------|
| [factor] | [Process/Technical/Communication/External] | [details] |

## What Went Well

- [list of things that worked]

## What Could Be Improved

- [list of improvement areas]

## Action Items

| ID | Action | Owner | Priority | Status |
|----|--------|-------|----------|--------|
| A1 | [action] | [owner] | [P1/P2/P3] | Open |

## Lessons Learned

[Structured lessons — these will be added to napkin]

## Graph Analysis (if available)

- **Blast Radius**: [N] features affected through [M] dependency paths
- **Unresolved Conflicts**: [any conflicts-with edges that contributed]
- **Predicted Threats**: [any threatens edges that foresaw this]
```

### 6. Auto-Generate Napkin Entries

For each lesson learned, create a structured napkin entry:

- **Category**: Appropriate category (IMPLEMENTATION, ARCHITECTURE, TEST, PERFORMANCE, etc.)
- **Context**: Feature and incident context
- **What Went Wrong**: From root cause analysis
- **What Fixed It**: Immediate fix and prevention measures
- **Lesson Learned**: The distilled lesson
- **Impact**: Time lost, users affected, severity
- **Prevention**: Specific process or technical prevention
- **Tags**: Relevant tags for future filtering
- **Distillation Status**: New

Write entries to `.specify/memory/napkin.md`.

### 7. Propose Constitution Amendments (if systemic)

If the root cause reveals a systemic issue (recurring pattern, process gap, or fundamental architecture concern):

- Draft a proposed constitution principle or amendment
- Show the evidence from this retrospective and any matching napkin patterns
- Ask user: "This appears to be a systemic issue. Would you like to propose a constitution amendment?"
- If yes, format as a constitution proposal for `/speckit.napkin-distill` or `/speckit.constitution`

### 8. Update Index and Report

- Update `.specify/memory/handovers/index.md` if a retrospective creates follow-up work
- Report: path to retrospective file, napkin entries created, constitution proposals if any
- Suggest next actions: "Run `/speckit.napkin-review` to check for patterns across retrospectives"

## Guidelines

- **Blameless**: Never attribute issues to individuals; focus on systems and processes
- **Forward-looking**: Every finding should have an actionable prevention measure
- **Concise**: Keep retrospective reports under 500 lines
- **Connected**: Link to specs, plans, tasks, and graph nodes wherever possible
- **Regular**: Recommend running after every feature completion, not just incidents
