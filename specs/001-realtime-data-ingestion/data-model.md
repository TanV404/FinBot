# Data Model: Real-Time Data Ingestion Pipeline

**Feature**: 001-realtime-data-ingestion
**Phase**: 1 — Design

---

## New Entities

### IngestionRun

Represents a single execution of the data pipeline. Created when a run starts; updated when it ends.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `run_id` | TEXT | PK, UUID, NOT NULL | Unique identifier for the run |
| `trigger` | TEXT | NOT NULL, `scheduled` or `manual` | What initiated this run |
| `started_at` | DATETIME | NOT NULL | ISO 8601 timestamp when the run began |
| `completed_at` | DATETIME | NULLABLE | ISO 8601 timestamp when the run ended (null while running) |
| `status` | TEXT | NOT NULL | One of: `running`, `completed`, `failed`, `rolled_back` |
| `companies_attempted` | INTEGER | NOT NULL, default 0 | Total companies the pipeline tried to fetch |
| `companies_succeeded` | INTEGER | NOT NULL, default 0 | Companies where fetch + ingest succeeded |
| `companies_failed` | INTEGER | NOT NULL, default 0 | Companies where any step failed |
| `failure_details` | TEXT | NULLABLE, JSON array | `[{"symbol": "TCS", "error": "connection timeout"}]` |
| `rollback_triggered` | INTEGER | NOT NULL, default 0 | 1 if the graph was rolled back after this run |

**Storage**: `ingestion_runs` table in existing SQLite database (`nifty_chat_history.db`)

**Indexes**:
- `started_at DESC` — for efficient history queries (last N runs)
- `status` — for quick "is any run currently running?" check

**State Transitions**:
```
[trigger received]
       │
       ▼
   running ──── fetch/ingest completes ──► completed
       │                                      
       │── fetch/ingest critically fails ──► failed
       │                                      
       └── rollback threshold not met ──────► rolled_back
```

**Validation Rules**:
- `completed_at` must be NULL when `status = 'running'`
- `companies_succeeded + companies_failed = companies_attempted` when status is terminal
- `failure_details` must be valid JSON array or NULL

---

### PipelineConfig

Runtime configuration for the pipeline. Not stored in the database — read from environment variables at startup.

| Config Key | Default Value | Description |
|------------|---------------|-------------|
| `PIPELINE_SCHEDULE_CRON` | `30 13 * * 1-5` | APScheduler cron expression (UTC). Default: Mon–Fri 18:30 IST (13:30 UTC). |
| `PIPELINE_ROLLBACK_THRESHOLD` | `0.80` | Minimum fraction of companies that must succeed for the new graph to be committed. |
| `PIPELINE_MAX_HISTORY` | `10` | Number of past IngestionRun records returned by the status endpoint. |
| `PIPELINE_REQUEST_TIMEOUT` | `30` | Per-company HTTP request timeout in seconds. |
| `PIPELINE_ENABLED` | `true` | Set to `false` to disable the scheduler without removing the code. |

---

## Modified Entities (Existing)

### KnowledgeGraph (data/networkx/nifty_graph.pkl)

No schema changes. The pipeline continues to write a `NetworkX.MultiDiGraph` with the same node/edge structure. The hot-reload mechanism is additive:

| Change | Description |
|--------|-------------|
| Backup file | Before each run writes a new graph, the previous `nifty_graph.pkl` is copied to `nifty_graph.previous.pkl` as a rollback target |
| Temp write path | New graph is written to `nifty_graph.tmp.pkl` then atomically renamed to `nifty_graph.pkl` on success |
| Mtime tracking | `NiftyGraphRetriever` tracks the last-loaded mtime and reloads if the file is newer |

### VectorStore (data/chromadb/)

No schema changes. The pipeline wipes and rebuilds ChromaDB exactly as `ingest.py` does today, then appends community summaries as `communities.py` does. The only change is timing — this now happens automatically on schedule rather than manually.

---

## SQLite Schema Changes

```sql
-- Add to existing database (nifty_chat_history.db)
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id              TEXT PRIMARY KEY,
    trigger             TEXT NOT NULL CHECK (trigger IN ('scheduled', 'manual')),
    started_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        DATETIME,
    status              TEXT NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'completed', 'failed', 'rolled_back')),
    companies_attempted INTEGER NOT NULL DEFAULT 0,
    companies_succeeded INTEGER NOT NULL DEFAULT 0,
    companies_failed    INTEGER NOT NULL DEFAULT 0,
    failure_details     TEXT,        -- JSON array: [{"symbol": "X", "error": "Y"}]
    rollback_triggered  INTEGER NOT NULL DEFAULT 0 CHECK (rollback_triggered IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_started_at
    ON ingestion_runs (started_at DESC);

CREATE INDEX IF NOT EXISTS idx_ingestion_runs_status
    ON ingestion_runs (status);
```

**Migration notes**:
- Non-destructive: adding a new table to an existing DB. No existing rows are affected.
- On server startup, the pipeline store runs `CREATE TABLE IF NOT EXISTS` — same pattern as `_ensure_summaries_table()` in `main.py`.
- On restart-recovery: any rows with `status = 'running'` at startup are updated to `status = 'failed'` with `completed_at = CURRENT_TIMESTAMP` and a note in `failure_details`.

---

## Entity Relationships

```
PipelineConfig ──(configures)──► PipelineRunner
PipelineRunner ──(creates)──────► IngestionRun
PipelineRunner ──(reads/writes)─► KnowledgeGraph
PipelineRunner ──(reads/writes)─► VectorStore
PipelineRunner ──(reads)────────► Company (yFinance + Wikipedia raw sources)

IngestionRun ──(stored in)──────► SQLite: ingestion_runs table
KnowledgeGraph ──(read by)──────► NiftyGraphRetriever (hot-reload on mtime change)
VectorStore ──(read by)─────────► HybridNiftyRetriever (similarity search)
```
