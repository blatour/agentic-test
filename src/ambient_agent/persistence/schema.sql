-- Ambient Agent persistence schema (SQLite).
-- All tables are bootstrapped idempotently via CREATE TABLE IF NOT EXISTS.
-- TEXT primary keys hold deterministic hex IDs (SHA-256 prefix or UUID).
-- Foreign keys are enforced at runtime via PRAGMA foreign_keys = ON.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- One row per agent wake cycle.
CREATE TABLE IF NOT EXISTS cycles (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',  -- running | ok | partial-failure | failed
    mode TEXT,
    source_count INTEGER NOT NULL DEFAULT 0,
    ok_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Canonical inbound events from all sources.
-- UNIQUE(source, source_event_id) enables idempotent insert / dedupe.
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    source TEXT NOT NULL,
    source_event_id TEXT,
    raw_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ok',  -- ok | fetch-error | parse-error | error
    fetched_at TEXT NOT NULL,
    latency_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(source, source_event_id)
);

-- Model analysis outputs tied to events and cycles.
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    event_id TEXT REFERENCES events(id),
    model TEXT,
    severity TEXT,
    summary TEXT,
    recommendation TEXT,
    raw_response TEXT,
    is_mock INTEGER NOT NULL DEFAULT 0,
    analyzed_at TEXT NOT NULL,
    latency_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Decision artifacts: notifications or follow-up tasks.
CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    analysis_id TEXT REFERENCES analyses(id),
    action_type TEXT NOT NULL,  -- notify | alert | suppress | follow-up
    payload TEXT NOT NULL,      -- JSON blob
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | sent | failed | suppressed
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    dispatched_at TEXT
);

-- Agent knowledge state: current projected view keyed by (source, key).
-- ON CONFLICT REPLACE allows the compare step to upsert the latest snapshot.
CREATE TABLE IF NOT EXISTS knowledge_state (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    source TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,        -- JSON blob
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE(source, key)
);

-- ChangeSet entries produced by the compare step each cycle.
CREATE TABLE IF NOT EXISTS changesets (
    id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL REFERENCES cycles(id),
    source TEXT NOT NULL,
    key TEXT NOT NULL,
    change_type TEXT NOT NULL,  -- added | removed | updated | unchanged
    old_value TEXT,             -- JSON blob; NULL for added entries
    new_value TEXT,             -- JSON blob; NULL for removed entries
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- Indexes supporting common query patterns.
CREATE INDEX IF NOT EXISTS idx_events_cycle     ON events(cycle_id);
CREATE INDEX IF NOT EXISTS idx_events_source    ON events(source, fetched_at);
CREATE INDEX IF NOT EXISTS idx_analyses_cycle   ON analyses(cycle_id);
CREATE INDEX IF NOT EXISTS idx_analyses_event   ON analyses(event_id);
CREATE INDEX IF NOT EXISTS idx_actions_cycle    ON actions(cycle_id);
CREATE INDEX IF NOT EXISTS idx_actions_status   ON actions(status);
CREATE INDEX IF NOT EXISTS idx_ks_source_key    ON knowledge_state(source, key);
CREATE INDEX IF NOT EXISTS idx_changesets_cycle ON changesets(cycle_id);
