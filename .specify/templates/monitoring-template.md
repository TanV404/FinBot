# Monitoring Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Tech Stack**: [from plan.md]

## Service Level Indicators (SLIs)

| ID | SLI | Data Source | Measurement | Derived From |
|----|-----|------------|-------------|--------------|
| SLI-001 | [e.g., Request latency] | [e.g., Application metrics] | [e.g., p50, p95, p99 in ms] | [e.g., SC-001] |
| SLI-002 | [e.g., Error rate] | [e.g., HTTP response codes] | [e.g., % of 5xx responses] | [e.g., SC-002] |

## Service Level Objectives (SLOs)

| SLI | Target | Window | Error Budget |
|-----|--------|--------|-------------|
| SLI-001 | [e.g., p95 < 500ms] | [e.g., 30-day rolling] | [e.g., 0.1% of requests] |
| SLI-002 | [e.g., < 1% error rate] | [e.g., 7-day rolling] | [e.g., 1% of requests] |

## Logging Requirements

### Request/Response Logging

| Endpoint | Log Level | Fields | Retention |
|----------|-----------|--------|-----------|
| [e.g., POST /api/users] | INFO | [e.g., user_id, action, duration_ms, status] | [e.g., 30 days] |

### Business Event Logging

| Event | Trigger | Fields | Level |
|-------|---------|--------|-------|
| [e.g., User registered] | [e.g., Account creation] | [e.g., user_id, method, timestamp] | INFO |

### Error Logging

| Error Category | Context Fields | Level |
|---------------|---------------|-------|
| [e.g., Validation failure] | [e.g., field, value, constraint] | WARN |
| [e.g., External service timeout] | [e.g., service, endpoint, timeout_ms] | ERROR |

## Alert Definitions

| ID | Name | Condition | Severity | Notification |
|----|------|-----------|----------|-------------|
| ALT-001 | [e.g., High latency] | [e.g., p95 > 1000ms for 5min] | P2 | [e.g., Slack #alerts] |
| ALT-002 | [e.g., Error spike] | [e.g., Error rate > 5% for 3min] | P1 | [e.g., PagerDuty] |

## Dashboard Specifications

### Overview Dashboard

| Panel | Visualization | Query/Metric |
|-------|--------------|-------------|
| [e.g., Request Rate] | [e.g., Time series graph] | [e.g., requests per second by endpoint] |
| [e.g., Error Rate] | [e.g., Gauge] | [e.g., 5xx / total requests %] |

### Business Metrics Dashboard

| Panel | Visualization | Query/Metric | Derived From |
|-------|--------------|-------------|--------------|
| [e.g., Registrations] | [e.g., Counter] | [e.g., user.registered events/day] | [e.g., SC-003] |

## Health Checks

| Check | Type | Endpoint/Method | Expected | Interval |
|-------|------|----------------|----------|----------|
| [e.g., Service liveness] | Liveness | [e.g., GET /health] | [e.g., 200 OK] | [e.g., 10s] |
| [e.g., Database connectivity] | Readiness | [e.g., DB ping] | [e.g., < 100ms] | [e.g., 30s] |
| [e.g., External API] | Dependency | [e.g., GET /external/health] | [e.g., 200 OK] | [e.g., 60s] |
