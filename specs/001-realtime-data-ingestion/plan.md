# Implementation Plan: Real-Time Data Ingestion Pipeline

**Branch**: `001-realtime-data-ingestion` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-realtime-data-ingestion/spec.md`

## Summary

Replace FinBot's one-shot manual data pipeline (`fetch_data.py` → `ingest.py` → `communities.py`) with an automated, scheduled pipeline that runs daily after NSE market close, hot-reloads the knowledge graph into the running server without downtime, and exposes two new REST endpoints for pipeline monitoring and manual triggering.

The implementation adds a `backend/pipeline/` package (scheduler, runner, SQLite store) and makes targeted changes to `retriever.py` (mtime-based hot-reload), `ingest.py` and `communities.py` (expose callable functions), and `main.py` (register pipeline routes + scheduler lifecycle). No new infrastructure is required.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: FastAPI (existing), APScheduler 3.10+ (new), pytest + pytest-asyncio (new, required by constitution TDD gate)  
**Storage**: SQLite (`nifty_chat_history.db`) — new `ingestion_runs` table; NetworkX pkl (existing, atomic swap); ChromaDB (existing, full rebuild per run)  
**Testing**: pytest + pytest-asyncio; httpx for endpoint integration tests  
**Target Platform**: Single Linux/Windows server running FastAPI + Uvicorn + Ollama  
**Performance Goals**: Full pipeline run completes in ≤ 45 minutes; graph hot-reload adds < 1ms overhead per retriever query (mtime stat only)  
**Constraints**: Zero chat-session downtime during pipeline run; no concurrent runs; atomic graph swap to prevent partial-file reads  
**Scale/Scope**: 50 NIFTY companies per run; daily schedule; ≤ 10 run history records queried at a time

## Security Considerations

**Authentication**: N/A — pipeline endpoints follow existing FinBot convention (no auth layer). If auth is added to the main API in the future, pipeline endpoints inherit it.  
**Authorization**: N/A — same trust model as existing `/health`, `/sessions` endpoints.  
**Data Protection**: No PII involved. Pipeline fetches public financial data and Wikipedia content. SQLite run history contains only ticker symbols and error messages.  
**Threat Assumptions**: Local network only (pipeline endpoints not exposed to the public internet in the current deployment). No injection risk — trigger endpoint accepts no user-controlled input.  
**Compliance**: N/A  
**Input Validation**: `POST /pipeline/trigger` accepts an empty body; no user input to validate. `GET /pipeline/status` is read-only.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| **Test-Driven Development (NON-NEGOTIABLE)** | ✅ REQUIRED | Unit tests for `runner.py`, `store.py`, and `scheduler.py` must be written before implementation. Integration tests for `/pipeline/status` and `/pipeline/trigger` endpoints required. |

*Other constitution principles are template placeholders and do not apply gates to this feature.*

**Gate result**: PASS — TDD requirement acknowledged and planned. Tests are scoped in the Project Structure below.

## Project Structure

### Documentation (this feature)

```text
specs/001-realtime-data-ingestion/
├── plan.md                   # This file
├── spec.md                   # Feature specification
├── research.md               # Phase 0 decisions
├── data-model.md             # Entity/schema design
├── quickstart.md             # Developer setup guide
├── contracts/
│   └── pipeline-api.yaml     # OpenAPI contract for /pipeline/* endpoints
├── dependency-graph.json     # Feature-level dependency graph
└── checklists/
    └── requirements.md       # Spec quality checklist
```

### Source Code (repository root)

```text
backend/
├── main.py                         # MODIFIED: scheduler lifecycle + pipeline routes
├── retriever.py                    # MODIFIED: mtime hot-reload in NiftyGraphRetriever
├── ingest.py                       # MODIFIED: ingest_all() becomes a callable function
├── communities.py                  # MODIFIED: process_communities() becomes callable
├── pipeline/
│   ├── __init__.py                 # NEW
│   ├── runner.py                   # NEW: PipelineRunner orchestrator
│   ├── scheduler.py                # NEW: APScheduler setup
│   └── store.py                    # NEW: IngestionRun SQLite CRUD
└── tests/
    ├── test_pipeline_runner.py     # NEW: TDD unit tests for runner
    ├── test_pipeline_store.py      # NEW: TDD unit tests for store
    └── test_pipeline_endpoints.py  # NEW: integration tests for API endpoints

fetch_data.py                       # UNCHANGED (root-level script still works manually)
.env                                # MODIFIED: document PIPELINE_* variables
```

**Structure Decision**: Web application (Option 2 from template). Backend-only changes — no frontend modifications. The `backend/pipeline/` sub-package is introduced to keep pipeline logic isolated from the main `backend/` modules.

## Migration Strategy

**Affected Entities**: SQLite database (`nifty_chat_history.db`) — adding `ingestion_runs` table.
**Backward Compatibility**: Yes — adding a new table does not affect existing `message_store` or `session_summaries` tables.
**Migration Approach**: `CREATE TABLE IF NOT EXISTS` run at server startup (same pattern as `_ensure_summaries_table()` in `main.py`). No data migration needed.
**Rollback Plan**: `DROP TABLE ingestion_runs;` — trivially reversible with no impact on chat data.
**Data Volume Considerations**: Table starts empty; grows by 1 row per pipeline run (at most ~365 rows/year). Negligible.
**Testing Strategy**: Test the `ensure_runs_table()` function in isolation against an in-memory SQLite database.

## Phase 0: Research

*Completed. See [research.md](./research.md) for all decisions.*

Key decisions resolved:
- **Scheduler**: APScheduler `AsyncIOScheduler` in FastAPI lifespan
- **Hot-reload**: Atomic file swap + mtime lazy-reload in retriever
- **Rebuild**: Full rebuild per run (not incremental)
- **Persistence**: New `ingestion_runs` table in existing SQLite
- **Rollback threshold**: 0.80 (configurable via `PIPELINE_ROLLBACK_THRESHOLD`)
- **Default schedule**: Mon–Fri 18:30 IST (`30 13 * * 1-5` UTC, configurable via `PIPELINE_SCHEDULE_CRON`)

## Phase 1: Design

*Completed. See [data-model.md](./data-model.md), [contracts/pipeline-api.yaml](./contracts/pipeline-api.yaml), [quickstart.md](./quickstart.md).*

### Component Responsibilities

#### `backend/pipeline/store.py` — IngestionRun persistence
- `ensure_runs_table(db_path)` — idempotent table creation
- `create_run(db_path, trigger) -> IngestionRun` — inserts a `running` row, returns run object
- `update_run(db_path, run_id, **fields)` — updates status, counts, completed_at
- `get_current_run(db_path) -> IngestionRun | None` — returns any `running` row
- `get_history(db_path, limit=10) -> list[IngestionRun]` — last N completed runs
- `recover_orphaned_runs(db_path)` — marks any `running` rows as `failed` on startup

#### `backend/pipeline/runner.py` — Pipeline orchestration
- `PipelineRunner` class
- `run(trigger: str) -> IngestionRun` — async method: fetch → ingest → communities → atomic swap → update run record
- Internal: per-company fetch with timeout + failure isolation
- Internal: rollback logic (rename `.tmp` → discard; restore `.previous`)
- Internal: calls refactored `ingest_all()` and `process_communities()` callables

#### `backend/pipeline/scheduler.py` — APScheduler wiring
- `build_scheduler(runner: PipelineRunner) -> AsyncIOScheduler`
- Reads `PIPELINE_SCHEDULE_CRON` and `PIPELINE_ENABLED` from environment
- Adds scheduled job calling `runner.run("scheduled")`
- Exposes `scheduler` instance for FastAPI lifespan start/stop

#### `backend/main.py` changes
- Lifespan: call `ensure_runs_table()`, `recover_orphaned_runs()`, `scheduler.start()` on startup; `scheduler.shutdown()` on shutdown
- Route `GET /pipeline/status` → query `store.get_current_run()` + `store.get_history()`
- Route `POST /pipeline/trigger` → check if running (409 if yes), else `asyncio.create_task(runner.run("manual"))`

#### `backend/retriever.py` changes
- `NiftyGraphRetriever.__init__`: record `self._graph_mtime = os.stat(graph_path).st_mtime`
- `NiftyGraphRetriever._get_relevant_documents`: before anchors, call `self._maybe_reload()`
- `_maybe_reload()`: stat the file; if mtime changed, acquire a threading.Lock, reload graph, update mtime

#### `backend/ingest.py` changes
- Extract body of `if __name__ == "__main__": ingest_all()` to be callable as `ingest_all(graph_path=None, chroma_path=None)` with defaults from env — preserves existing CLI usage while enabling programmatic calls.

#### `backend/communities.py` changes
- Same pattern: `process_communities(graph_path=None, chroma_path=None)` callable with env defaults.

### TDD Test Plan

| Test File | Tests to Write First (Red) |
|-----------|---------------------------|
| `test_pipeline_store.py` | `test_create_run_returns_running_status`, `test_update_run_sets_completed`, `test_recover_orphaned_marks_failed`, `test_get_history_returns_n_records` |
| `test_pipeline_runner.py` | `test_run_succeeds_all_companies`, `test_run_with_partial_failures_commits_above_threshold`, `test_run_below_threshold_triggers_rollback`, `test_concurrent_run_rejected` |
| `test_pipeline_endpoints.py` | `test_status_returns_200_when_idle`, `test_status_shows_running_when_pipeline_active`, `test_trigger_starts_run`, `test_trigger_rejects_when_running` |

## Complexity Tracking

No constitution violations. The `backend/pipeline/` sub-package is justified by separation of concerns — mixing scheduler, runner, and persistence code into `main.py` would make that file harder to test and reason about.
