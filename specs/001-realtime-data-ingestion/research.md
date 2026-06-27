# Research: Real-Time Data Ingestion Pipeline

**Feature**: 001-realtime-data-ingestion
**Phase**: 0 — Resolve unknowns before design

---

## Decision 1: Scheduler Approach

**Question**: How should periodic pipeline runs be triggered — in-process scheduler, OS cron, or separate worker?

**Decision**: APScheduler (in-process, asyncio-compatible) integrated with the FastAPI lifespan.

**Rationale**:
- FinBot runs as a single Python process (FastAPI + Uvicorn). Adding APScheduler keeps the scheduler in the same process, shares the same environment variables and DB connection, and requires zero additional infrastructure.
- APScheduler's `AsyncIOScheduler` integrates cleanly with FastAPI's `asynccontextmanager` lifespan: start scheduler on startup, stop on shutdown.
- OS cron is simpler but requires the pipeline and the web server to coordinate externally (e.g., via a lock file or a second process), which increases operational complexity for no benefit at this scale.
- Celery + message broker (Redis/RabbitMQ) adds significant infrastructure overhead that is not justified for a single-server, 50-company use case.

**Alternatives considered**:
- OS cron + subprocess: rejected because it cannot prevent concurrent runs with the web server's in-memory state or share the async lock.
- `asyncio.sleep` loop in FastAPI lifespan: simpler but inflexible (can't use cron syntax, harder to trigger manually).
- APScheduler chosen for cron-expression support and minimal footprint.

---

## Decision 2: Knowledge Graph Hot-Reload (No Restart)

**Question**: How does the running `HybridNiftyRetriever` pick up a newly ingested graph without a server restart?

**Decision**: Atomic file swap + modification-time (mtime) lazy reload in the retriever.

**Rationale**:
- The pipeline writes the new graph to a `.tmp` file, then uses `os.replace()` (atomic on POSIX and Windows NTFS) to overwrite the live path. This prevents any reader from loading a partially-written file.
- `NiftyGraphRetriever` caches `_G` (the NetworkX graph) as a PrivateAttr. A lightweight check on `os.stat(graph_path).st_mtime` at the start of each `_get_relevant_documents()` call determines whether to reload. The stat call is ~0.01ms — negligible.
- A `threading.Lock` (or `asyncio.Lock` promoted to thread-safe via `asyncio.run_coroutine_threadsafe`) guards the reload to prevent a concurrent query from reading a half-loaded graph during reload.
- Alternative (signal-based reload): would require catching SIGUSR1 inside the process — complex on Windows and doesn't fit the existing codebase.
- Alternative (full restart): zero-downtime rolling restart is complex for a single-server setup; violates FR-009 (no session interruption).

---

## Decision 3: Incremental vs Full Rebuild

**Question**: Should the pipeline update only changed company data (incremental) or rebuild the full graph from scratch each run?

**Decision**: Full rebuild per run for the initial version.

**Rationale**:
- The existing pipeline always does a full rebuild (`ingest_all()` calls `os.remove(GRAPH_PATH)` and `shutil.rmtree(CHROMA_PATH)` at the start). Reusing this logic minimises risk of graph corruption from partial updates.
- 50 companies × ~2s per fetch = ~100s of network I/O. Graph build and vector embedding take the bulk of the 45-minute SLA. A full rebuild is well within the SLA.
- Incremental logic (hash-based change detection + partial graph updates) is correct but significantly more complex. NetworkX's `MultiDiGraph.update()` semantics for partial merges require careful deduplication of VALUE_AT edges. The risk of subtle data inconsistency outweighs the performance gain at this scale.
- Incremental can be added as a follow-on optimisation once the full-rebuild pipeline is stable and proven.

---

## Decision 4: IngestionRun Persistence

**Question**: Where should pipeline run history (IngestionRun records) be stored?

**Decision**: A new `ingestion_runs` table in the existing SQLite database (`nifty_chat_history.db`).

**Rationale**:
- The SQLite database is already managed by the backend and is guaranteed to exist when the pipeline runs.
- Adding one table avoids introducing a second storage system.
- SQLite's single-writer model is appropriate — pipeline runs are infrequent (at most a few per day) and status queries are lightweight reads.
- A JSON flat file was considered but rejected: concurrent access handling, atomic writes, and query filtering are harder with a flat file than with SQLite.

---

## Decision 5: Rollback Threshold (resolves spec FR-010 clarification)

**Question**: What percentage of successful company updates should trigger an automatic rollback if not met?

**Decision**: Configurable via `PIPELINE_ROLLBACK_THRESHOLD` env var, **defaulting to 0.80** (40/50 companies must succeed; if fewer do, the new graph is discarded and the previous one is retained).

**Rationale**:
- 80% is a reasonable default: it allows up to 10 companies to fail (e.g., due to temporary API timeouts) while still committing a substantially fresh graph.
- Making it configurable (env var) allows operators to tighten or loosen the threshold without code changes, satisfying FR-012's spirit.
- A rollback retains the `.previous.pkl` backup created before each run starts.

---

## Decision 6: Default Ingestion Schedule (resolves spec FR-012 clarification)

**Question**: Should the default schedule be daily post-market-close (18:30 IST weekdays) or a simpler fixed 24-hour interval?

**Decision**: **Daily at 18:30 IST, Monday–Friday** (cron: `30 13 * * 1-5` in UTC, i.e., 18:30 IST = 13:00 UTC).

**Rationale**:
- NSE closes at 15:30 IST; yFinance's daily data is typically available by 18:00 IST. Running at 18:30 IST ensures complete daily financials are available.
- Skipping weekends avoids 104 unnecessary runs/year when market data does not change.
- The schedule is overridable via `PIPELINE_SCHEDULE_CRON` env var for flexibility.

---

## Decision 7: Concurrency Guard Implementation

**Question**: How is the "no concurrent runs" constraint (FR-008) enforced?

**Decision**: An `asyncio.Lock` held for the duration of each run, with the current status also reflected in the `ingestion_runs` SQLite table.

**Rationale**:
- The asyncio lock prevents concurrent triggers within the same process (covers both scheduled and manual triggers running in the same event loop).
- The SQLite `status = 'running'` row provides a secondary guard and makes the "is running" state visible to the status API without additional in-memory state.
- If the server restarts mid-run, the SQLite row will remain in `running` state. On startup, the pipeline store will detect any orphaned `running` rows and mark them `failed` (restart recovery).

---

## Dependencies to Install

| Package | Version | Purpose |
|---------|---------|---------|
| `apscheduler` | ≥ 3.10 | In-process async scheduler |
| `pytest` | ≥ 8.0 | Unit/integration testing (TDD — required by constitution) |
| `pytest-asyncio` | ≥ 0.23 | Async test support |
| `httpx` | already used in evaluate_rag.py | HTTP testing of new endpoints |

No new infrastructure (no Redis, no separate worker process).
