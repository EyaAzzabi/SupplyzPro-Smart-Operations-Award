-- X-Ray database schema.
-- One SQLite file, populated by database/seed_db.py from the AI layer's
-- output (ai/run_pipeline.py). The backend reads from this, never from
-- the raw JSON files, once seeded.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS batches (
    batch_id            TEXT PRIMARY KEY,      -- 'before' | 'after'
    total_conversations INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT NOT NULL,
    batch_id        TEXT NOT NULL REFERENCES batches(batch_id),
    workflow        TEXT NOT NULL,
    failure_type    TEXT,                      -- ground-truth label, synthetic data only
    PRIMARY KEY (conversation_id, batch_id)
);

-- One row per turn in a conversation. turn_number is the position within
-- the conversation (matches the AI layer's turn_id), not a global id.
CREATE TABLE IF NOT EXISTS turns (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id  TEXT NOT NULL,
    batch_id         TEXT NOT NULL,
    turn_number      INTEGER NOT NULL,
    role             TEXT NOT NULL,             -- 'user' | 'agent'
    text             TEXT NOT NULL,
    FOREIGN KEY (conversation_id, batch_id) REFERENCES conversations(conversation_id, batch_id)
);

-- At most one tool call per turn (agent turns that call a tool).
CREATE TABLE IF NOT EXISTS tool_calls (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id          INTEGER NOT NULL REFERENCES turns(id),
    tool_name        TEXT NOT NULL,
    parameters_json  TEXT NOT NULL,
    response_json    TEXT,
    latency_ms       INTEGER,
    error_code       TEXT,
    idempotency_key  TEXT
);

CREATE TABLE IF NOT EXISTS clusters (
    cluster_id        INTEGER NOT NULL,
    batch_id          TEXT NOT NULL REFERENCES batches(batch_id),
    label             TEXT NOT NULL,
    failure_type      TEXT NOT NULL,
    frequency         INTEGER NOT NULL,
    severity          INTEGER NOT NULL,
    blast_radius      INTEGER NOT NULL,
    priority_score    INTEGER NOT NULL,
    workflows_touched TEXT NOT NULL,            -- comma-separated
    PRIMARY KEY (cluster_id, batch_id)
);

CREATE TABLE IF NOT EXISTS failure_instances (
    instance_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id        INTEGER NOT NULL,
    batch_id          TEXT NOT NULL,
    conversation_id   TEXT NOT NULL,
    detector          TEXT NOT NULL,
    failure_type      TEXT NOT NULL,
    description       TEXT NOT NULL,
    evidence_turn_ids TEXT NOT NULL,            -- comma-separated turn_number values
    FOREIGN KEY (cluster_id, batch_id) REFERENCES clusters(cluster_id, batch_id)
);

CREATE TABLE IF NOT EXISTS regression_probes (
    probe_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id           INTEGER NOT NULL,
    batch_id             TEXT NOT NULL,
    top_failure_type     TEXT NOT NULL,
    top_cluster_label    TEXT NOT NULL,
    frequency_before_fix INTEGER NOT NULL,
    frequency_after_fix  INTEGER NOT NULL,
    pass_rate            REAL,
    conversation_id      TEXT NOT NULL,
    caught               INTEGER NOT NULL,      -- 0/1
    FOREIGN KEY (cluster_id, batch_id) REFERENCES clusters(cluster_id, batch_id)
);

-- One Agent 4 root-cause explanation per batch-scoped cluster.
CREATE TABLE IF NOT EXISTS root_causes (
    root_cause_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id          INTEGER NOT NULL,
    batch_id            TEXT NOT NULL,
    failure_type        TEXT NOT NULL,
    explanation         TEXT NOT NULL,
    contributing_factors TEXT NOT NULL,         -- JSON array
    UNIQUE (cluster_id, batch_id),
    FOREIGN KEY (cluster_id, batch_id) REFERENCES clusters(cluster_id, batch_id)
);

-- One Agent 5 ranking record per batch-scoped cluster.
CREATE TABLE IF NOT EXISTS priority_scores (
    priority_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id          INTEGER NOT NULL,
    batch_id            TEXT NOT NULL,
    frequency           INTEGER NOT NULL,
    severity            INTEGER NOT NULL,
    blast_radius        INTEGER NOT NULL,
    score               INTEGER NOT NULL,
    rank                INTEGER NOT NULL,
    UNIQUE (cluster_id, batch_id),
    FOREIGN KEY (cluster_id, batch_id) REFERENCES clusters(cluster_id, batch_id)
);

-- One Agent 6 aggregate replay comparison per tested cluster. Probe outcomes
-- remain JSON because version 1 does not persist full replay transcripts.
CREATE TABLE IF NOT EXISTS fix_replays (
    replay_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id          INTEGER NOT NULL,
    batch_id            TEXT NOT NULL,
    failure_type        TEXT NOT NULL,
    replay_mode         TEXT NOT NULL CHECK (replay_mode IN ('aggregate', 'full')),
    frequency_before_fix INTEGER NOT NULL,
    frequency_after_fix  INTEGER NOT NULL,
    pass_rate            REAL,
    probes_json         TEXT NOT NULL,           -- JSON array of probe outcomes
    UNIQUE (cluster_id, batch_id),
    FOREIGN KEY (cluster_id, batch_id) REFERENCES clusters(cluster_id, batch_id)
);

CREATE INDEX IF NOT EXISTS idx_turns_conversation ON turns(conversation_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_turn ON tool_calls(turn_id);
CREATE INDEX IF NOT EXISTS idx_clusters_batch_score ON clusters(batch_id, priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_failure_instances_cluster ON failure_instances(cluster_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_failure_instances_conversation ON failure_instances(conversation_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_root_causes_cluster ON root_causes(cluster_id, batch_id);
CREATE INDEX IF NOT EXISTS idx_priority_scores_rank ON priority_scores(batch_id, rank);
CREATE INDEX IF NOT EXISTS idx_fix_replays_cluster ON fix_replays(cluster_id, batch_id);
