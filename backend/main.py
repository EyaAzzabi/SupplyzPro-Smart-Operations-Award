"""X-Ray API -- serves the database to the frontend.

Run: uvicorn backend.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = Path(__file__).parent.parent / "database" / "xray.db"

app = FastAPI(title="X-Ray API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon demo: any origin. Lock this down before real deployment.
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail="Database not seeded yet. Run `python -m database.seed_db`.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/summary")
def get_summary():
    conn = get_conn()
    total_conversations = conn.execute(
        "SELECT total_conversations FROM batches WHERE batch_id = 'before'"
    ).fetchone()["total_conversations"]
    total_failures = conn.execute(
        "SELECT COALESCE(SUM(frequency), 0) AS n FROM clusters WHERE batch_id = 'before'"
    ).fetchone()["n"]
    cluster_count = conn.execute(
        "SELECT COUNT(*) AS n FROM clusters WHERE batch_id = 'before'"
    ).fetchone()["n"]
    conn.close()
    return {
        "total_conversations": total_conversations,
        "total_failures": total_failures,
        "cluster_count": cluster_count,
    }


@app.get("/api/clusters")
def get_clusters(batch: str = "before"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT cluster_id, label, failure_type, frequency, severity, blast_radius, "
        "priority_score, workflows_touched FROM clusters WHERE batch_id = ? "
        "ORDER BY priority_score DESC",
        (batch,),
    ).fetchall()
    conn.close()
    return [
        {
            "cluster_id": r["cluster_id"],
            "label": r["label"],
            "failure_type": r["failure_type"],
            "frequency": r["frequency"],
            "severity": r["severity"],
            "blast_radius": r["blast_radius"],
            "priority_score": r["priority_score"],
            "workflows_touched": r["workflows_touched"].split(","),
        }
        for r in rows
    ]


@app.get("/api/clusters/{cluster_id}/evidence")
def get_cluster_evidence(cluster_id: int, batch: str = "before"):
    conn = get_conn()
    cluster = conn.execute(
        "SELECT * FROM clusters WHERE cluster_id = ? AND batch_id = ?", (cluster_id, batch)
    ).fetchone()
    if cluster is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Cluster not found")

    instances = conn.execute(
        "SELECT * FROM failure_instances WHERE cluster_id = ? AND batch_id = ?", (cluster_id, batch)
    ).fetchall()

    evidence = []
    for inst in instances:
        conv_row = conn.execute(
            "SELECT turns_json FROM conversations WHERE conversation_id = ? AND batch_id = ?",
            (inst["conversation_id"], batch),
        ).fetchone()
        turns = json.loads(conv_row["turns_json"]) if conv_row else []
        evidence.append({
            "conversation_id": inst["conversation_id"],
            "detector": inst["detector"],
            "description": inst["description"],
            "evidence_turn_ids": [int(t) for t in inst["evidence_turn_ids"].split(",")],
            "turns": turns,
        })
    conn.close()

    return {
        "cluster_id": cluster["cluster_id"],
        "label": cluster["label"],
        "instances": evidence,
    }


@app.get("/api/fix-comparison")
def get_fix_comparison():
    conn = get_conn()
    probes = conn.execute("SELECT * FROM regression_probes").fetchall()
    conn.close()
    if not probes:
        raise HTTPException(status_code=404, detail="No regression probe data available")

    first = probes[0]
    return {
        "top_failure_type": first["top_failure_type"],
        "top_cluster_label": first["top_cluster_label"],
        "frequency_before_fix": first["frequency_before_fix"],
        "frequency_after_fix": first["frequency_after_fix"],
        "pass_rate": first["pass_rate"],
        "probes": [
            {"conversation_id": p["conversation_id"], "caught": bool(p["caught"])}
            for p in probes
        ],
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
