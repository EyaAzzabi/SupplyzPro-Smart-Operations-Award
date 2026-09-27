-- X-Ray database schema.
-- One SQLite file, populated by database/seed_db.py from the AI layer's
-- output (ai/run_pipeline.py). The backend reads from this, never from
-- the raw JSON files, once seeded.

CREATE TABLE IF NOT EXISTS batches (
    batch_id        TEXT PRIMARY KEY,      -- 'before' | 'after'
    total_conversations INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT NOT NULL,
    batch_id        TEXT NOT NULL REFERENCES batches(batch_id),
    workflow        TEXT NOT NULL,
    failure_type    TEXT,                  -- ground-truth label, synthetic data only
    turns_json       TEXT NOT NULL,        -- full turn/tool-call transcript, as JSON
    PRIMARY KEY (conversation_id, batch_id)
);

CREATE TABLE IF NOT EXISTS clusters (
    cluster_id      INTEGER NOT NULL,
    batch_id        TEXT NOT NULL REFERENCES batches(batch_id),
    label           TEXT NOT NULL,
    failure_type    TEXT NOT NULL,
    frequency       INTEGER NOT NULL,
    severity        INTEGER NOT NULL,
    blast_radius    INTEGER NOT NULL,
    priority_score  INTEGER NOT NULL,
    workflows_touched TEXT NOT NULL,       -- comma-separated
    PRIMARY KEY (cluster_id, batch_id)
);

CREATE TABLE IF NOT EXISTS failure_instances (
    instance_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id       INTEGER NOT NULL,
    batch_id         TEXT NOT NULL,
    conversation_id  TEXT NOT NULL,
    detector         TEXT NOT NULL,
    failure_type     TEXT NOT NULL,
    description      TEXT NOT NULL,
    evidence_turn_ids TEXT NOT NULL,       -- comma-separated turn ids
    FOREIGN KEY (cluster_id, batch_id) REFERENCES clusters(cluster_id, batch_id)
);

CREATE TABLE IF NOT EXISTS regression_probes (
    probe_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    top_failure_type    TEXT NOT NULL,
    top_cluster_label   TEXT NOT NULL,
    frequency_before_fix INTEGER NOT NULL,
    frequency_after_fix  INTEGER NOT NULL,
    pass_rate           REAL,
    conversation_id      TEXT NOT NULL,
    caught               INTEGER NOT NULL  -- 0/1
);
