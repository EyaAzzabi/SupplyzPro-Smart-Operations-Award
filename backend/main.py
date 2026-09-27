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
                "SELECT explanation, contributing_factors "
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

        try:
            contributing_factors = json.loads(root_cause["contributing_factors"])
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail="Malformed root-cause data") from exc

        return {
            "cluster_id": cluster["cluster_id"],
            "batch_id": cluster["batch_id"],
            "label": cluster["label"],
            "failure_type": cluster["failure_type"],
            "explanation": root_cause["explanation"],
            "contributing_factors": contributing_factors,
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


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str, batch: str = "before"):
    conn = get_conn()
    try:
        conversation = conn.execute(
            "SELECT conversation_id, batch_id, workflow, failure_type "
            "FROM conversations WHERE conversation_id = ? AND batch_id = ?",
            (conversation_id, batch),
        ).fetchone()
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {
            "conversation_id": conversation["conversation_id"],
            "batch_id": conversation["batch_id"],
            "workflow": conversation["workflow"],
            "failure_type": conversation["failure_type"],
            "turns": _get_turns(conn, conversation_id, batch),
        }
    finally:
        conn.close()


@app.get("/api/failures")
def get_failures(batch: str = "before"):
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT instance_id, cluster_id, batch_id, conversation_id, detector, "
            "failure_type, description, evidence_turn_ids "
            "FROM failure_instances WHERE batch_id = ? ORDER BY instance_id",
            (batch,),
        ).fetchall()
        return [
            {
                "instance_id": row["instance_id"],
                "cluster_id": row["cluster_id"],
                "batch_id": row["batch_id"],
                "conversation_id": row["conversation_id"],
                "detector": row["detector"],
                "failure_type": row["failure_type"],
                "description": row["description"],
                "evidence_turn_ids": [int(turn_id) for turn_id in row["evidence_turn_ids"].split(",")],
            }
            for row in rows
        ]
    finally:
        conn.close()


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


@app.get("/api/fix-comparison")
def get_fix_comparison():
    conn = get_conn()
    try:
        try:
            first = conn.execute(
                "SELECT cluster_id, batch_id FROM fix_replays ORDER BY replay_id LIMIT 1"
            ).fetchone()
        except sqlite3.OperationalError as exc:
            if "no such table: fix_replays" not in str(exc):
                raise
            first = None
        if first is None:
            try:
                first = conn.execute(
                    "SELECT cluster_id, batch_id FROM regression_probes "
                    "ORDER BY probe_id LIMIT 1"
                ).fetchone()
            except sqlite3.OperationalError as exc:
                if "no such table: regression_probes" in str(exc):
                    first = None
                else:
                    raise
        if first is None:
            raise HTTPException(status_code=404, detail="No fix replay data available")
        return _build_fix_comparison(conn, first["cluster_id"], first["batch_id"])
    finally:
        conn.close()


def _build_fix_comparison(conn, cluster_id, batch):
    try:
        replay = conn.execute(
            "SELECT r.cluster_id, r.batch_id, c.label, r.failure_type, "
            "r.frequency_before_fix, r.frequency_after_fix, r.pass_rate, r.probes_json "
            "FROM fix_replays r "
            "JOIN clusters c ON c.cluster_id = r.cluster_id AND c.batch_id = r.batch_id "
            "WHERE r.cluster_id = ? AND r.batch_id = ?",
            (cluster_id, batch),
        ).fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table: fix_replays" not in str(exc):
            raise
        replay = None

    if replay is not None:
        try:
            probes = json.loads(replay["probes_json"])
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail="Malformed fix replay data") from exc
        return {
            "cluster_id": replay["cluster_id"],
            "batch_id": replay["batch_id"],
            "top_failure_type": replay["failure_type"],
            "top_cluster_label": replay["label"],
            "frequency_before_fix": replay["frequency_before_fix"],
            "frequency_after_fix": replay["frequency_after_fix"],
            "pass_rate": replay["pass_rate"],
            "probes": [
                {"conversation_id": probe["conversation_id"], "caught": bool(probe["caught"])}
                for probe in probes
            ],
        }

    try:
        probes = conn.execute(
            "SELECT * FROM regression_probes WHERE cluster_id = ? AND batch_id = ? "
            "ORDER BY probe_id",
            (cluster_id, batch),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table: regression_probes" in str(exc):
            probes = []
        else:
            raise
    if not probes:
        raise HTTPException(status_code=404, detail="No fix replay data for this cluster")

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
            {"conversation_id": probe["conversation_id"], "caught": bool(probe["caught"])}
            for probe in probes
        ],
    }


@app.get("/api/clusters/{cluster_id}/fix-comparison")
def get_cluster_fix_comparison(cluster_id: int, batch: str = "before"):
    conn = get_conn()
    try:
        cluster = conn.execute(
            "SELECT cluster_id FROM clusters WHERE cluster_id = ? AND batch_id = ?",
            (cluster_id, batch),
        ).fetchone()
        if cluster is None:
            raise HTTPException(status_code=404, detail="Cluster not found")
        return _build_fix_comparison(conn, cluster_id, batch)
    finally:
        conn.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
