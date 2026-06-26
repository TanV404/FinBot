# Feature Specification: Real-Time Data Ingestion Pipeline

**Feature Branch**: `001-realtime-data-ingestion`
**Created**: 2026-06-16
**Status**: Draft
**Review Status**: Draft
**Version**: 1.0
**Input**: User description: "Add a real time data ingestion pipeline"

## Overview

Today, FinBot's knowledge graph is built once by manually running batch scripts (`fetch_data.py` → `ingest.py` → `communities.py`). Once the data is ingested, it stays frozen until someone runs those scripts again. Users may unknowingly receive answers based on outdated financial figures.

This feature replaces that manual, one-shot workflow with an automated ingestion pipeline that keeps FinBot's knowledge graph continuously fresh. After implementation, financial data for all NIFTY 50 companies will be refreshed on a recurring schedule, users will receive answers grounded in current data, and operators will have visibility into when data was last updated and whether the pipeline is healthy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Fresh Answers from Current Financial Data (Priority: P1)

A FinBot user asks about a company's revenue or net profit. Today, the answer reflects whenever the data scripts were last run — potentially weeks or months ago. After this feature, the answer reflects data refreshed within the last 24 hours (or per the configured schedule).

**Why this priority**: This is the core value of a "real-time" pipeline. If FinBot answers with stale data, user trust erodes. Everything else in this feature is secondary to ensuring the data served to users is current.

**Independent Test**: Can be fully tested by asking FinBot "What is TCS's revenue?" immediately after a pipeline run completes, and verifying the answer matches the latest yFinance data — delivering the value of freshness without needing any other story.

**Acceptance Scenarios**:

1. **Given** a pipeline run has completed within the last 24 hours, **When** a user asks for a NIFTY 50 company's latest financial metric, **Then** FinBot's answer reflects the data from that run, not from any earlier run.
2. **Given** a pipeline run just completed, **When** FinBot is queried immediately, **Then** there is no restart or downtime — active sessions continue uninterrupted.
3. **Given** the pipeline run updated 48 of 50 companies (2 failed), **When** a user asks about one of the 48 successfully updated companies, **Then** they receive fresh data; when they ask about a failed company, they receive the last known data (not an error).

---

### User Story 2 — Pipeline Status Visibility for Operators (Priority: P2)

A system operator wants to know whether the pipeline is running correctly. They need to see: when the last run happened, how many companies were updated successfully, and whether any errors occurred.

**Why this priority**: Without observability, operators cannot distinguish between "the pipeline is working" and "the pipeline silently failed three days ago." Visibility is essential for maintaining data quality.

**Independent Test**: Can be fully tested by querying a pipeline status endpoint after a run and verifying it returns last-run timestamp, companies updated count, and any error details — delivering operational confidence independently of the chat feature.

**Acceptance Scenarios**:

1. **Given** a pipeline run has just completed, **When** an operator queries the pipeline status, **Then** they see the start time, end time, number of companies successfully updated, and a list of any companies that failed with their error reason.
2. **Given** no pipeline run has ever been executed, **When** an operator queries status, **Then** they receive a clear "no runs recorded" response rather than an error.
3. **Given** the last three pipeline runs all failed for the same company, **When** an operator views status history, **Then** they can see the pattern of repeated failures for that company.

---

### User Story 3 — On-Demand Manual Refresh (Priority: P3)

A system operator wants to immediately refresh data for all companies — for example, after a major market event or to test that the pipeline is working correctly — without waiting for the next scheduled run.

**Why this priority**: Scheduled runs handle the common case; manual triggers handle exceptional circumstances. This story extends value without blocking P1 or P2.

**Independent Test**: Can be tested by calling a "trigger refresh" action and confirming a new ingestion run starts and completes, updating the knowledge graph — independently of the scheduling mechanism.

**Acceptance Scenarios**:

1. **Given** the pipeline is idle, **When** an operator triggers a manual refresh, **Then** a new ingestion run begins immediately and completes within the expected time window.
2. **Given** a scheduled run is already in progress, **When** an operator attempts to trigger a manual refresh, **Then** the system rejects the request with a clear message that a run is already underway.
3. **Given** a manual refresh completes, **When** an operator queries pipeline status, **Then** the status reflects the manual run as the most recent run.

---

### Edge Cases

- What happens when a data source (yFinance or Wikipedia) is temporarily unreachable during a run? The pipeline must continue updating all other companies and record the unreachable ones as failed.
- What happens when a run is in progress and FinBot receives a chat query? The query must be served using the last committed knowledge graph state — not a partially updated one.
- What happens when newly fetched data for a company is structurally malformed (e.g., missing all financial metrics)? The pipeline must reject the update for that company and retain the previous valid data.
- What happens when the pipeline runs but no data has changed since the last run? The system should still record a successful run; no unnecessary graph rebuilding should occur.
- What happens if two manual refresh triggers are sent simultaneously? Only one run should proceed; the second must be rejected with an appropriate message.
- What happens when the pipeline has been inactive for more than 48 hours? The status endpoint must clearly flag this as a staleness warning, not silently show an old timestamp.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically fetch updated financial data (income statement, balance sheet, shareholding) and company profile information for all 50 NIFTY companies on a configurable recurring schedule.
- **FR-002**: The system MUST update the knowledge graph with newly fetched data so that subsequent FinBot queries reflect the refreshed information without requiring a system restart or redeployment.
- **FR-003**: The system MUST update the vector knowledge base with refreshed company text content after each successful ingestion run.
- **FR-004**: The system MUST record a structured log for every ingestion run, capturing: run start time, run end time, total companies attempted, count of successful updates, count of failures, and per-company error details for any failures.
- **FR-005**: The system MUST expose a queryable status resource that returns the most recent run record and a configurable history of past runs (default: last 10 runs).
- **FR-006**: The system MUST continue the pipeline run when any individual company's data fetch fails — a single company failure MUST NOT abort updates for the remaining companies.
- **FR-007**: The system MUST allow an operator to trigger a data refresh on demand via an explicit action.
- **FR-008**: The system MUST prevent concurrent pipeline runs — if a run is already in progress, any new trigger (scheduled or manual) MUST be rejected until the current run completes.
- **FR-009**: The system MUST NOT interrupt or degrade active chat sessions while a pipeline run is in progress; queries during a run MUST be served from the last fully committed knowledge graph state.
- **FR-010**: The system MUST retain the previous knowledge graph state as a fallback if a pipeline run produces a critically incomplete result (fewer than 40 of 50 companies successfully updated). [NEEDS CLARIFICATION: What threshold of failure should trigger a rollback — is 40/50 the right boundary, or should it be configurable?]
- **FR-011**: The system MUST expose the timestamp of the last successful data refresh so it can be surfaced to users when relevant (e.g., included in API responses or chat metadata).
- **FR-012**: The ingestion schedule MUST be configurable without modifying source code (e.g., via an environment variable or configuration file). [NEEDS CLARIFICATION: Should the schedule default to daily post-market-close (e.g., 18:30 IST weekdays only), or should it run on a simpler fixed interval (e.g., every 24 hours regardless of market hours)?]

### Key Entities

- **IngestionRun**: Represents a single execution of the pipeline. Key attributes: run ID, trigger type (scheduled/manual), start time, end time, status (running/completed/failed/rolled-back), companies attempted, companies succeeded, companies failed, error details per failed company.
- **CompanySnapshot**: The data fetched for a single company during one ingestion run. Key attributes: company symbol, fetch timestamp, data source (financial/profile/wiki), raw content hash (to detect unchanged data), and parse success flag.
- **PipelineConfig**: The configuration governing pipeline behaviour. Key attributes: schedule expression, failure threshold for rollback, request timeout per company, maximum concurrent company fetches.
- **KnowledgeGraph** *(existing)*: The graph of companies, sectors, metrics, and relationships — updated by each successful ingestion run.
- **VectorStore** *(existing)*: The embedded knowledge base of company text content — refreshed after each run.

## Assumptions

- "Real-time" in this context means **near-real-time via scheduled periodic updates**, not sub-second streaming. Financial data from public APIs updates at most daily (after market close), so daily scheduled runs are the appropriate default.
- The data sources (yFinance for financials, Wikipedia for company profiles) remain the same as the existing batch pipeline. Switching data providers is out of scope.
- Community summary regeneration (graph clustering + LLM summarization) is **included** in the pipeline run since community summaries feed into the retriever. A run that updates the graph but not the community summaries would leave the two out of sync.
- The pipeline will run on the same server as the FinBot backend. Distributed job scheduling infrastructure is out of scope.
- Wikipedia content changes infrequently compared to financial data. The pipeline will always attempt to refresh both, but a hash comparison may be used to skip re-embedding unchanged wiki content.
- No authentication is required to query the pipeline status endpoint, as FinBot currently has no authentication layer. This may need revisiting if auth is added later.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Financial data for all 50 NIFTY companies is refreshed and available to users within 45 minutes of a scheduled pipeline run starting.
- **SC-002**: During normal operation, users receive answers based on data no more than 24 hours old (assuming the default daily schedule).
- **SC-003**: A single company's data-fetch failure does not delay or prevent updates for the other 49 companies — the partial run completes within the same 45-minute window.
- **SC-004**: An operator can determine the last successful refresh timestamp and any errors in under 10 seconds by querying the status endpoint.
- **SC-005**: Active chat sessions experience zero downtime or degraded response quality during a pipeline run.
- **SC-006**: At least 95% of scheduled pipeline runs complete with 45 or more of 50 companies successfully updated, without requiring manual intervention.
- **SC-007**: A manually triggered refresh starts within 5 seconds of the operator's request and completes in under 45 minutes.

## Dependencies

- Existing `fetch_data.py` logic (yFinance + Wikipedia fetching) — will be adapted, not replaced.
- Existing `ingest.py` logic (graph building + ChromaDB population) — will be invoked as part of the pipeline.
- Existing `communities.py` logic (community detection + LLM summarization) — will be invoked after graph update.
- The FinBot backend (`main.py`) must be able to hot-reload the knowledge graph without restarting the server process.

## Out of Scope

- Real-time streaming of market tick data (intraday price feeds).
- Adding new data sources beyond yFinance and Wikipedia.
- A visual dashboard UI for pipeline monitoring (the status API endpoint satisfies P2; a UI can be a follow-on feature).
- Alerting / notification (e.g., email/Slack on pipeline failure) — this is a valuable follow-on but not part of this specification.
- Multi-server or distributed pipeline execution.

## Change Log

| Version | Date | Change | Rationale |
|---------|------|--------|-----------|
| 1.0 | 2026-06-16 | Initial specification | Created from feature description "Add a real time data ingestion pipeline" |
