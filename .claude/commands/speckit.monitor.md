---
description: "Generate an observability and monitoring specification for the feature based on its design artifacts"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Produce a monitoring specification that defines what to log, what to alert on, what dashboards to create, and what health checks to implement for the current feature. Derived from the feature's spec (success criteria), plan (tech stack), and dependency graph (component topology).

## Operating Constraints

- **Writes monitoring.md only**: Creates `FEATURE_DIR/monitoring.md` using the monitoring template.
- **Technology-aware**: Adapt recommendations to the actual tech stack from plan.md.
- **Graph-enhanced**: If dependency graph exists, use it to identify all endpoints, external dependencies, and entity state transitions that need monitoring.

## Execution Steps

### 0. Load Memory Context

- Read `.specify/memory/napkin.md` (skip if doesn't exist)
- Filter for entries about production incidents, monitoring gaps, or observability issues
- Apply lessons to prioritize monitoring for historically problematic areas

### 1. Initialize Context

Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse JSON for FEATURE_DIR and AVAILABLE_DOCS.

Required: `spec.md`, `plan.md`
Optional: `data-model.md`, `contracts/`, `dependency-graph.json`

### 2. Extract Monitoring Inputs

**From spec.md**:
- Success criteria → SLI/SLO candidates (e.g., "under 2 minutes" → latency SLO)
- User stories → key user journeys to monitor
- Edge cases → error scenarios to alert on

**From plan.md**:
- Tech stack → appropriate monitoring tools and patterns
- External dependencies → health check targets
- Performance goals → threshold values for alerts

**From data-model.md** (if exists):
- Entity state transitions → state change metrics
- Data integrity constraints → validation monitoring

**From contracts/** (if exists):
- API endpoints → per-endpoint latency, error rate, throughput metrics
- Error response definitions → specific error alert conditions

**From dependency-graph.json** (if exists):
- Endpoint nodes → comprehensive list of endpoints to instrument
- External dependency edges → services to health-check
- Entity nodes with state transitions → state machine monitoring
- Hub file nodes → code hotspots worth extra monitoring

### 3. Generate Monitoring Specification

Load `.specify/templates/monitoring-template.md` and populate:

**SLIs (Service Level Indicators)**:
- Derive from success criteria in spec.md
- Each SLI must be measurable and have a clear data source

**SLOs (Service Level Objectives)**:
- Target values derived from success criteria and performance goals
- Error budgets where applicable

**Logging Requirements**:
- Per-endpoint: request/response logging at appropriate levels
- Business events: key user actions and state transitions
- Error logging: structured error events with context

**Alert Definitions**:
- Threshold alerts for SLO violations
- Rate-based alerts for error spikes
- Absence alerts for expected periodic events
- Severity classification: P1 (page) / P2 (notify) / P3 (log)

**Dashboard Specifications**:
- Overview dashboard: key SLIs, request rates, error rates
- Per-endpoint dashboards: latency percentiles, throughput, error breakdown
- Business metrics dashboard: feature-specific KPIs from success criteria

**Health Checks**:
- Liveness: is the service running?
- Readiness: can the service handle requests?
- Dependency checks: are external services reachable?

### 4. Write Monitoring Specification

Write the completed specification to `FEATURE_DIR/monitoring.md`.

### 5. Report

Output:
- Path to generated monitoring.md
- Summary: [N] SLIs, [M] alerts, [K] dashboard panels defined
- Any gaps: success criteria without corresponding SLIs
- Suggested implementation priority: which monitoring to add first
