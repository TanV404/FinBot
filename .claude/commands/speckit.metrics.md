---
description: "Collect and display process metrics for the Spec-Driven Development workflow, measuring framework effectiveness"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Collect metrics from `.specify/` artifacts to measure the effectiveness of the Spec-Driven Development process. Tracks feature pipeline completion, specification quality, estimation accuracy, graph coverage, and learning velocity. Outputs a dashboard summary with trends.

## Operating Constraints

- **Read-only on artifacts**: Reads specs, plans, tasks, napkin, handovers, graph, and retrospectives.
- **Writes metrics.json**: Appends timestamped metric snapshots to `.specify/metrics.json`.
- **No external dependencies**: All data comes from local `.specify/` artifacts.

## Execution Steps

### 1. Scan Project Artifacts

Collect raw data from the project:

**Feature Pipeline Metrics** (scan `specs/` directories):
- Total features created (count `specs/*/` directories)
- Features with spec.md
- Features with plan.md
- Features with tasks.md
- Features with complete pipeline (spec + plan + tasks + all tasks marked [x])
- Pipeline completion rate: features with full pipeline / total features

**Specification Quality Metrics** (scan `specs/*/spec.md`):
- Average [NEEDS CLARIFICATION] markers per spec
- Specs with Review Status: Approved vs. Draft vs. In Review
- Average number of functional requirements per spec
- Average number of user stories per spec
- Specs with checklist files (checklists/ directory)

**Task & Estimation Metrics** (scan `specs/*/tasks.md`):
- Total tasks across all features
- Completed tasks ([x]) vs. incomplete ([ ])
- Average tasks per feature
- If [Est:N] markers present:
  - Total estimated story points
  - Completed story points
  - Average estimation per task

**Napkin & Learning Metrics** (read `.specify/memory/napkin.md`):
- Total napkin entries
- Entries by category (SPEC, PLAN, IMPLEMENTATION, TEST, etc.)
- Entries by severity (CRITICAL, HIGH, MEDIUM, LOW)
- Total estimated time lost (from Impact fields)
- Constitution amendments triggered (Distillation Status: Constitutionalized)

**Handover Metrics** (scan `.specify/memory/handovers/`):
- Total handover sessions
- Active vs. archived handovers
- Average session frequency (handovers per week)
- If effort tracking present:
  - Average velocity (points per session)
  - Estimated vs. actual effort accuracy

**Retrospective Metrics** (scan `.specify/memory/retrospectives/`):
- Total retrospectives conducted
- Incident postmortems vs. feature retrospectives
- Action items generated vs. resolved

**Graph Metrics** (read `.specify/graphs/index.json` if exists):
- Total graph nodes and edges
- Graph coverage: % of source files (in `src/` or equivalent) that have graph nodes
- Graph staleness: nodes referencing files that no longer exist or have been modified
- Hub nodes: files with fan-in > 5
- Cross-feature edges: edges connecting nodes from different features
- Conflict edges: edges with `conflicts-with` relation
- Resolved vs. unresolved conflicts

### 2. Compute Derived Metrics

- **SDD Adoption Rate**: features with full pipeline / total features
- **Spec Quality Score**: (approved specs * 3 + reviewed specs * 2 + draft specs * 1) / total specs
- **Learning Velocity**: napkin entries per feature (higher = more learning captured)
- **Estimation Accuracy**: if actual effort tracked, compute actual / estimated ratio
- **Graph Health**: (nodes with edges / total nodes) * coverage%

### 3. Save Metrics Snapshot

Append to `.specify/metrics.json`:

```json
{
  "timestamp": "ISO-8601",
  "pipeline": {
    "total_features": 12,
    "complete_pipeline": 8,
    "completion_rate": 0.67
  },
  "quality": {
    "avg_clarifications": 1.5,
    "approved_specs": 6,
    "avg_requirements": 7.2
  },
  "tasks": {
    "total": 234,
    "completed": 189,
    "total_points": 412,
    "completed_points": 334
  },
  "learning": {
    "napkin_entries": 23,
    "time_lost_hours": 18.5,
    "constitution_amendments": 3
  },
  "graph": {
    "total_nodes": 156,
    "total_edges": 287,
    "coverage_pct": 73,
    "staleness_pct": 5,
    "hub_count": 4,
    "unresolved_conflicts": 1
  }
}
```

### 4. Display Dashboard

```markdown
## Spec-Driven Development Metrics Dashboard

**Snapshot**: [timestamp]
**Project**: [repo name]

### Pipeline Health

| Metric | Value | Trend |
|--------|-------|-------|
| Features Created | [N] | |
| Full Pipeline Completion | [N]% | [up/down vs. last snapshot] |
| Avg Tasks per Feature | [N] | |
| Task Completion Rate | [N]% | |

### Specification Quality

| Metric | Value | Trend |
|--------|-------|-------|
| Approved Specs | [N] of [M] | |
| Avg Clarification Questions | [N] | [lower is better] |
| Avg Requirements per Spec | [N] | |
| Specs with Checklists | [N]% | |

### Estimation & Effort

| Metric | Value | Trend |
|--------|-------|-------|
| Total Story Points Estimated | [N] | |
| Story Points Completed | [N] | |
| Avg Velocity (pts/session) | [N] | |
| Estimation Accuracy | [N]% | [closer to 100% is better] |

### Learning & Improvement

| Metric | Value | Trend |
|--------|-------|-------|
| Napkin Entries | [N] | |
| Time Lost (hours) | [N] | [lower is better] |
| Constitution Amendments | [N] | |
| Retrospectives Conducted | [N] | |

### Dependency Graph Health (if available)

| Metric | Value | Trend |
|--------|-------|-------|
| Graph Coverage | [N]% | [higher is better] |
| Graph Staleness | [N]% | [lower is better] |
| Hub Modules | [N] | |
| Cross-Feature Edges | [N] | |
| Unresolved Conflicts | [N] | [0 is ideal] |

### Recommendations

[Based on metrics, suggest specific improvements]
```

### 5. Trend Analysis (if multiple snapshots exist)

If `.specify/metrics.json` contains previous snapshots:
- Compare current metrics to previous snapshots
- Show trend direction (improving / declining / stable) for each metric
- Highlight significant changes (>10% improvement or decline)
- Suggest focus areas based on declining metrics

## Guidelines

- Run periodically (e.g., weekly or after each feature completion)
- Metrics are local and opt-in — no external telemetry
- Focus on trends, not absolute numbers — every project is different
- Use metrics to identify process bottlenecks, not to judge individuals
- If a metric consistently shows poor results, suggest a specific SDD workflow change
