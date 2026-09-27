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
            "(conversation_id, batch_id, workflow, failure_type, turns_json) VALUES (?, ?, ?, ?, ?)",
            (conv_id, batch_id, conv["workflow"], conv.get("failure_type"), json.dumps(conv["turns"])),
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


def main():
    before = json.loads((RESULTS_DIR / "results_before.json").read_text())
    after = json.loads((RESULTS_DIR / "results_after.json").read_text())
    probes_path = RESULTS_DIR / "regression_probes.json"
    probes = json.loads(probes_path.read_text()) if probes_path.exists() else None

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    _insert_batch(conn, "before", before, before["conversations_by_id"])
    # the "after" batch's conversations aren't needed for evidence drill-down
    # (there's nothing to show -- that's the point), only its cluster stats
    _insert_batch(conn, "after", after, {})

    if probes:
        for probe in probes["probes"]:
            conn.execute(
                "INSERT INTO regression_probes "
                "(top_failure_type, top_cluster_label, frequency_before_fix, frequency_after_fix, "
                "pass_rate, conversation_id, caught) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    probes["top_failure_type"], probes["top_cluster_label"],
                    probes["frequency_before_fix"], probes["frequency_after_fix"],
                    probes["pass_rate"], probe["conversation_id"], int(probe["caught"]),
                ),
            )

    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH}")


if __name__ == "__main__":
    main()
