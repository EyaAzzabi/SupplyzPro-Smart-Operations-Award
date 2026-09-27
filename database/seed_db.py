"""Loads the AI layer's output (results/*.json) into xray.db.

The AI layer (ai/run_pipeline.py) stays storage-agnostic -- it just writes
JSON. This script is the one place that knows about the database, so the
backend never has to import anything from ai/ directly at request time,
except for ai.root_cause, which is cheap/deterministic and used here to
populate the root_causes table from the same logic the dashboards use.

Run: python -m database.seed_db
"""

import json
import sqlite3
from pathlib import Path

from ai.root_cause import analyze_root_cause

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"
DB_PATH = Path(__file__).parent / "xray.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _insert_batch(conn, batch_id, results, conversations_by_id, include_analysis=True):
    """`include_analysis` gates priority_scores/root_causes: they're only
    meaningful for the baseline ("before") batch. "after" cluster IDs are a
    fresh clustering run and aren't the same issues as "before"'s (see
    docs/backend-contract.md's cluster-identity note), so analyzing them
    would silently attach real-looking root-cause text to the wrong thing."""
    conn.execute(
        "INSERT OR REPLACE INTO batches (batch_id, total_conversations) VALUES (?, ?)",
        (batch_id, results["total_conversations"]),
    )

    for conv_id, conv in conversations_by_id.items():
        conn.execute(
            "INSERT OR REPLACE INTO conversations "
            "(conversation_id, batch_id, workflow, failure_type) VALUES (?, ?, ?, ?)",
            (conv_id, batch_id, conv["workflow"], conv.get("failure_type")),
        )
        for turn in conv["turns"]:
            cur = conn.execute(
                "INSERT INTO turns (conversation_id, batch_id, turn_number, role, text) "
                "VALUES (?, ?, ?, ?, ?)",
                (conv_id, batch_id, turn["turn_id"], turn["role"], turn["text"]),
            )
            tool_call = turn.get("tool_call")
            if tool_call:
                conn.execute(
                    "INSERT INTO tool_calls "
                    "(turn_id, tool_name, parameters_json, response_json, latency_ms, error_code, "
                    "idempotency_key) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        cur.lastrowid, tool_call["tool_name"], json.dumps(tool_call["parameters"]),
                        json.dumps(tool_call.get("response")), tool_call.get("latency_ms"),
                        tool_call.get("error_code"), tool_call.get("idempotency_key"),
                    ),
                )

    ranked_clusters = sorted(results["clusters"], key=lambda c: c["priority_score"], reverse=True)
    for rank, cluster in enumerate(ranked_clusters, start=1):
        conn.execute(
            "INSERT OR REPLACE INTO clusters "
            "(cluster_id, batch_id, label, failure_type, frequency, severity, blast_radius, "
            "priority_score, workflows_touched) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                cluster["cluster_id"], batch_id, cluster["label"], cluster["failure_type"],
                cluster["frequency"], cluster["severity"], cluster["blast_radius"],
                cluster["priority_score"], ",".join(cluster["workflows_touched"]),
            ),
        )
        if include_analysis:
            conn.execute(
                "INSERT OR REPLACE INTO priority_scores "
                "(cluster_id, batch_id, frequency, severity, blast_radius, score, rank) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    cluster["cluster_id"], batch_id, cluster["frequency"], cluster["severity"],
                    cluster["blast_radius"], cluster["priority_score"], rank,
                ),
            )
            root_cause = analyze_root_cause(cluster["failure_type"])
            conn.execute(
                "INSERT OR REPLACE INTO root_causes "
                "(cluster_id, batch_id, failure_type, explanation, confidence, contributing_factors, "
                "causal_chain) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    cluster["cluster_id"], batch_id, cluster["failure_type"], root_cause["root_cause"],
                    root_cause["confidence"], json.dumps(root_cause["contributing_factors"]),
                    json.dumps(root_cause["causal_chain"]),
                ),
            )
        for instance in cluster["instances"]:
            conn.execute(
                "INSERT INTO failure_instances "
                "(cluster_id, batch_id, conversation_id, detector, failure_type, description, "
                "evidence_turn_ids) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    cluster["cluster_id"], batch_id, instance["conversation_id"], instance["detector"],
                    instance["failure_type"], instance["description"],
                    ",".join(str(t) for t in instance["evidence_turn_ids"]),
                ),
            )


def seed_database(db_path, results_dir):
    """Rebuilds `db_path` from scratch using the pipeline output in
    `results_dir`. Split out from main() so tests can seed a temporary
    database without touching the real one."""
    before = json.loads((results_dir / "results_before.json").read_text())
    after = json.loads((results_dir / "results_after.json").read_text())
    probes_path = results_dir / "regression_probes.json"
    probes = json.loads(probes_path.read_text()) if probes_path.exists() else None

    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_PATH.read_text())

    _insert_batch(conn, "before", before, before["conversations_by_id"])
    # the "after" batch's conversations aren't needed for evidence drill-down
    # (there's nothing to show -- that's the point), only its cluster stats
    _insert_batch(conn, "after", after, {}, include_analysis=False)

    if probes:
        for probe in probes["probes"]:
            conn.execute(
                "INSERT INTO regression_probes "
                "(cluster_id, batch_id, top_failure_type, top_cluster_label, frequency_before_fix, "
                "frequency_after_fix, pass_rate, conversation_id, caught) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    probes["cluster_id"], probes.get("batch_id", "before"),
                    probes["top_failure_type"], probes["top_cluster_label"],
                    probes["frequency_before_fix"], probes["frequency_after_fix"],
                    probes["pass_rate"], probe["conversation_id"], int(probe["caught"]),
                ),
            )

    conn.commit()
    conn.close()
    return db_path


def main():
    seed_database(DB_PATH, RESULTS_DIR)
    print(f"Seeded {DB_PATH}")


if __name__ == "__main__":
    main()
