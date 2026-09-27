"""Loads the AI layer's output (results/*.json) into xray.db.

The AI layer (ai/run_pipeline.py) stays storage-agnostic -- it just writes
JSON. This script is the one place that knows about the database, so the
backend never has to import anything from ai/ directly at request time.

Run: python -m database.seed_db
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"
DB_PATH = Path(__file__).parent / "xray.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _insert_batch(conn, batch_id, results, conversations_by_id):
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

    for cluster in results["clusters"]:
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


def _insert_analysis(conn, analysis):
    if analysis.get("artifact_type") != "xray.agent_4_6_output":
        raise ValueError("unsupported Agent 4-6 artifact type")
    if analysis.get("schema_version") != 1:
        raise ValueError("unsupported Agent 4-6 schema version")

    for root_cause in analysis.get("root_causes", []):
        conn.execute(
            "INSERT OR REPLACE INTO root_causes "
            "(cluster_id, batch_id, failure_type, explanation, contributing_factors) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                root_cause["cluster_id"], root_cause["batch_id"], root_cause["failure_type"],
                root_cause["explanation"], json.dumps(root_cause["contributing_factors"]),
            ),
        )

    for priority in analysis.get("priority_scores", []):
        conn.execute(
            "INSERT OR REPLACE INTO priority_scores "
            "(cluster_id, batch_id, frequency, severity, blast_radius, score, rank) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                priority["cluster_id"], priority["batch_id"], priority["frequency"],
                priority["severity"], priority["blast_radius"], priority["score"],
                priority["rank"],
            ),
        )

    for replay in analysis.get("fix_replays", []):
        conn.execute(
            "INSERT OR REPLACE INTO fix_replays "
            "(cluster_id, batch_id, failure_type, replay_mode, frequency_before_fix, "
            "frequency_after_fix, pass_rate, probes_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                replay["cluster_id"], replay["batch_id"], replay["failure_type"],
                replay["replay_mode"], replay["frequency_before_fix"],
                replay["frequency_after_fix"], replay.get("pass_rate"),
                json.dumps(replay.get("probes", [])),
            ),
        )


def seed_database(db_path=DB_PATH, results_dir=RESULTS_DIR):
    before = json.loads((results_dir / "results_before.json").read_text())
    after = json.loads((results_dir / "results_after.json").read_text())
    analysis_path = results_dir / "agent_4_6_output.json"
    analysis = json.loads(analysis_path.read_text()) if analysis_path.exists() else None
    probes_path = results_dir / "regression_probes.json"
    probes = json.loads(probes_path.read_text()) if probes_path.exists() else None

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())

        _insert_batch(conn, "before", before, before["conversations_by_id"])
        # The after batch only needs cluster stats for the comparison.
        _insert_batch(conn, "after", after, {})

        if analysis:
            _insert_analysis(conn, analysis)

        if probes:
            for probe in probes["probes"]:
                conn.execute(
                    "INSERT INTO regression_probes "
                    "(cluster_id, batch_id, top_failure_type, top_cluster_label, "
                    "frequency_before_fix, frequency_after_fix, pass_rate, conversation_id, caught) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        probes["cluster_id"], probes["batch_id"], probes["top_failure_type"],
                        probes["top_cluster_label"], probes["frequency_before_fix"],
                        probes["frequency_after_fix"], probes["pass_rate"],
                        probe["conversation_id"], int(probe["caught"]),
                    ),
                )

        conn.commit()
    finally:
        conn.close()


def main():
    seed_database()
    print(f"Seeded {DB_PATH}")


if __name__ == "__main__":
    main()
