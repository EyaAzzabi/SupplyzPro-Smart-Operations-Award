"""X-Ray API -- serves the database to the frontend.

Run: uvicorn backend.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ai.impact import assess_impact
from ai.remediation import recommend_remediation
from ai.root_cause import analyze_root_cause

DB_PATH = Path(__file__).parent.parent / "database" / "xray.db"
EVALUATION_DIR = Path(__file__).parent.parent / "evaluation" / "results"

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


@app.get("/api/priority")
def get_priority(batch: str = "before"):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT p.cluster_id, p.batch_id, c.label, c.failure_type, "
            "p.frequency, p.severity, p.blast_radius, p.score, p.rank, "
            "c.workflows_touched "
            "FROM priority_scores p "
            "JOIN clusters c ON c.cluster_id = p.cluster_id AND c.batch_id = p.batch_id "
            "WHERE p.batch_id = ? ORDER BY p.rank ASC, p.score DESC",
            (batch,),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table: priority_scores" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="Priority data not seeded yet. Run `python -m database.seed_db`.",
            ) from exc
        raise
    finally:
        conn.close()

    return [
        {
            "cluster_id": row["cluster_id"],
            "batch_id": row["batch_id"],
            "label": row["label"],
            "failure_type": row["failure_type"],
            "frequency": row["frequency"],
            "severity": row["severity"],
            "blast_radius": row["blast_radius"],
            "score": row["score"],
            "rank": row["rank"],
            "workflows_touched": row["workflows_touched"].split(","),
        }
        for row in rows
    ]


@app.get("/api/clusters/{cluster_id}/root-cause")
def get_cluster_root_cause(cluster_id: int, batch: str = "before"):
    conn = get_conn()
    try:
        cluster = conn.execute(
            "SELECT cluster_id, batch_id, label, failure_type "
            "FROM clusters WHERE cluster_id = ? AND batch_id = ?",
            (cluster_id, batch),
        ).fetchone()
        if cluster is None:
            raise HTTPException(status_code=404, detail="Cluster not found")

        try:
            root_cause = conn.execute(
                "SELECT explanation, confidence, contributing_factors "
                "FROM root_causes WHERE cluster_id = ? AND batch_id = ?",
                (cluster_id, batch),
            ).fetchone()
        except sqlite3.OperationalError as exc:
            if "no such table: root_causes" in str(exc):
                raise HTTPException(
                    status_code=503,
                    detail="Root-cause data not seeded yet. Run `python -m database.seed_db`.",
                ) from exc
            raise

        if root_cause is None:
            raise HTTPException(status_code=404, detail="Root cause not found")

        return {
            "cluster_id": cluster["cluster_id"],
            "batch_id": cluster["batch_id"],
            "label": cluster["label"],
            "failure_type": cluster["failure_type"],
            "explanation": root_cause["explanation"],
            "confidence": root_cause["confidence"],
            "contributing_factors": json.loads(root_cause["contributing_factors"]),
        }
    finally:
        conn.close()


def _get_turns(conn, conversation_id, batch):
    rows = conn.execute(
        "SELECT t.id, t.turn_number, t.role, t.text, "
        "tc.tool_name, tc.parameters_json, tc.response_json, tc.latency_ms, tc.error_code "
        "FROM turns t LEFT JOIN tool_calls tc ON tc.turn_id = t.id "
        "WHERE t.conversation_id = ? AND t.batch_id = ? ORDER BY t.turn_number",
        (conversation_id, batch),
    ).fetchall()

    turns = []
    for r in rows:
        turn = {"turn_id": r["turn_number"], "role": r["role"], "text": r["text"]}
        if r["tool_name"] is not None:
            turn["tool_call"] = {
                "tool_name": r["tool_name"],
                "parameters": json.loads(r["parameters_json"]),
                "response": json.loads(r["response_json"]) if r["response_json"] else None,
                "latency_ms": r["latency_ms"],
                "error_code": r["error_code"],
            }
        turns.append(turn)
    return turns


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
        turns = _get_turns(conn, inst["conversation_id"], batch)
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


@app.get("/api/clusters/{cluster_id}/analysis")
def get_cluster_analysis(cluster_id: int, batch: str = "before"):
    conn = get_conn()
    cluster = conn.execute(
        "SELECT * FROM clusters WHERE cluster_id = ? AND batch_id = ?", (cluster_id, batch)
    ).fetchone()
    conn.close()
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    cluster_dict = {
        "failure_type": cluster["failure_type"],
        "frequency": cluster["frequency"],
        "severity": cluster["severity"],
        "blast_radius": cluster["blast_radius"],
        "priority_score": cluster["priority_score"],
        "workflows_touched": cluster["workflows_touched"].split(","),
    }
    return {
        "cluster_id": cluster["cluster_id"],
        "label": cluster["label"],
        "root_cause": analyze_root_cause(cluster["failure_type"]),
        "impact": assess_impact(cluster_dict),
        "remediation": recommend_remediation(cluster["failure_type"]),
    }


def _fix_comparison_payload(probes):
    first = probes[0]
    return {
        "cluster_id": first["cluster_id"],
        "batch_id": first["batch_id"],
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


@app.get("/api/fix-comparison")
def get_fix_comparison():
    """Legacy, unscoped route -- kept for the existing dashboards. New
    clients should use the cluster-scoped route below."""
    conn = get_conn()
    probes = conn.execute("SELECT * FROM regression_probes").fetchall()
    conn.close()
    if not probes:
        raise HTTPException(status_code=404, detail="No regression probe data available")
    return _fix_comparison_payload(probes)


@app.get("/api/clusters/{cluster_id}/fix-comparison")
def get_cluster_fix_comparison(cluster_id: int, batch: str = "before"):
    conn = get_conn()
    probes = conn.execute(
        "SELECT * FROM regression_probes WHERE cluster_id = ? AND batch_id = ?",
        (cluster_id, batch),
    ).fetchall()
    conn.close()
    if not probes:
        raise HTTPException(status_code=404, detail="No regression probe data for this cluster")
    return _fix_comparison_payload(probes)


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str, batch: str = "before"):
    conn = get_conn()
    conv = conn.execute(
        "SELECT conversation_id, workflow, failure_type FROM conversations "
        "WHERE conversation_id = ? AND batch_id = ?",
        (conversation_id, batch),
    ).fetchone()
    if conv is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    turns = _get_turns(conn, conversation_id, batch)
    conn.close()
    return {
        "conversation_id": conv["conversation_id"],
        "workflow": conv["workflow"],
        "failure_type": conv["failure_type"],
        "turns": turns,
    }


@app.get("/api/failures")
def get_failures(batch: str = "before"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT cluster_id, batch_id, conversation_id, detector, failure_type, description, "
        "evidence_turn_ids FROM failure_instances WHERE batch_id = ?",
        (batch,),
    ).fetchall()
    conn.close()
    return [
        {
            "cluster_id": r["cluster_id"],
            "batch_id": r["batch_id"],
            "conversation_id": r["conversation_id"],
            "detector": r["detector"],
            "failure_type": r["failure_type"],
            "description": r["description"],
            "evidence_turn_ids": [int(t) for t in r["evidence_turn_ids"].split(",")],
        }
        for r in rows
    ]


@app.get("/api/evaluation")
def get_evaluation():
    synthetic_path = EVALUATION_DIR / "metrics.json"
    real_world_path = EVALUATION_DIR / "real_world_metrics.json"
    if not synthetic_path.exists():
        raise HTTPException(status_code=503, detail="Evaluation not run yet. Run `python -m evaluation.run_evaluation`.")

    synthetic = json.loads(synthetic_path.read_text())
    real_world = None
    if real_world_path.exists():
        rw = json.loads(real_world_path.read_text())
        real_world = {k: v for k, v in rw.items() if k != "conversations"}

    return {"synthetic": synthetic, "real_world": real_world}


@app.get("/api/health")
def health():
    return {"status": "ok"}
