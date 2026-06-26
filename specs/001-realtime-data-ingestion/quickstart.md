# Quickstart: Real-Time Data Ingestion Pipeline

**Feature**: 001-realtime-data-ingestion

---

## What This Feature Does

Replaces the manual `fetch_data.py` → `ingest.py` → `communities.py` one-shot workflow with an automated pipeline that:

1. Fetches fresh NIFTY 50 financial data + Wikipedia content on a schedule
2. Rebuilds the knowledge graph and vector store
3. Hot-reloads the graph into the running FinBot server (no restart needed)
4. Records each run's outcome in SQLite
5. Exposes two new endpoints: `GET /pipeline/status` and `POST /pipeline/trigger`

---

## New Files Created

```
backend/
└── pipeline/
    ├── __init__.py          # Package marker
    ├── runner.py            # PipelineRunner — orchestrates fetch → ingest → communities
    ├── scheduler.py         # APScheduler setup, integrates with FastAPI lifespan
    └── store.py             # IngestionRun CRUD against SQLite

tests/
└── backend/
    ├── test_pipeline_runner.py      # Unit tests for runner logic (TDD)
    ├── test_pipeline_store.py       # Unit tests for SQLite persistence
    └── test_pipeline_endpoints.py  # Integration tests for /pipeline/* endpoints
```

---

## Changed Files

| File | Change |
|------|--------|
| `backend/main.py` | Add scheduler startup/shutdown in lifespan; register `GET /pipeline/status` and `POST /pipeline/trigger` routes |
| `backend/retriever.py` | Add mtime-based hot-reload to `NiftyGraphRetriever` |
| `backend/ingest.py` | Expose `ingest_all(graph_path, chroma_path)` as a callable (not just `if __name__ == "__main__"`) |
| `backend/communities.py` | Expose `process_communities(graph_path, chroma_path)` as a callable |
| `.env` / `.env.example` | Document new `PIPELINE_*` environment variables |

---

## Environment Variables

Add to `.env` (all optional — defaults shown):

```bash
# Pipeline schedule (APScheduler cron, UTC). Default: Mon-Fri 18:30 IST = 13:30 UTC
PIPELINE_SCHEDULE_CRON="30 13 * * 1-5"

# Minimum fraction of companies that must succeed for the graph to be committed
PIPELINE_ROLLBACK_THRESHOLD=0.80

# Number of past runs returned by GET /pipeline/status
PIPELINE_MAX_HISTORY=10

# Per-company fetch timeout in seconds
PIPELINE_REQUEST_TIMEOUT=30

# Set to false to disable the scheduler without removing the code
PIPELINE_ENABLED=true
```

---

## How to Verify It Works

### 1. Start the server
```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Check pipeline is idle
```bash
curl http://127.0.0.1:8000/pipeline/status
```
Expected: `{ "is_running": false, "last_successful_at": null, "staleness_warning": true, ... }`

### 3. Trigger a manual run
```bash
curl -X POST http://127.0.0.1:8000/pipeline/trigger
```
Expected: `{ "run_id": "...", "status": "started", "message": "..." }`

### 4. Poll for completion
```bash
curl http://127.0.0.1:8000/pipeline/status
```
Watch `is_running` transition from `true` to `false`, and `status` on the run move to `completed`.

### 5. Verify the chat uses fresh data
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is TCS revenue?", "session_id": "test-001"}'
```
The answer should reflect data fetched during the pipeline run.

---

## Running Tests (TDD — Required)

```bash
cd backend
pytest tests/ -v
```

Tests must be written first (Red) before any implementation code exists, per the project constitution.

---

## Key Design Decisions Summary

| Decision | Choice | Reason |
|----------|--------|--------|
| Scheduler | APScheduler in-process | No extra infrastructure; shares FastAPI process |
| Hot-reload | mtime check + atomic file rename | Zero-downtime; prevents partial-file reads |
| Rebuild strategy | Full rebuild per run | Matches existing pipeline; simpler than incremental |
| Run history store | SQLite (existing DB) | No new infrastructure; consistent with chat history |
| Rollback threshold | 0.80 (configurable) | 80% success = at most 10 failures trigger rollback |
| Default schedule | Mon–Fri 18:30 IST | Aligns with NSE market close |
