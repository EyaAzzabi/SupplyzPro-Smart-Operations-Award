"""Runs the full X-Ray pipeline end to end:

  1. load conversations (before/after)
  2. detect failures in layers (rules + LLM-judge + behavioral)
  3. cluster by root cause
  4. prioritize (Frequency x Severity x Blast Radius)
  5. for the top "before" cluster: generate regression probes and verify
     the detector catches them, and compare that cluster's frequency
     before vs. after the simulated fix
  6. for every "before" cluster: root cause, impact, and remediation
     (ai/root_cause.py, ai/impact.py, ai/remediation.py), assembled into
     an executive report (ai/executive_report.py)

Writes results/results_before.json, results/results_after.json,
results/regression_probes.json, and results/executive_report.{json,md}
for the dashboard and submission package to read.

Run: python -m ai.run_pipeline
"""

import json
from pathlib import Path

from ai.executive_report import build_executive_report, render_markdown
from ai.failure_detective import detect_failures
from ai.pattern_hunter import find_patterns
from ai.prioritize import prioritize
from ai.regression_probes import generate_and_run_probes
from ai.trace_investigator import normalize_traces

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def process_batch(conversations, batch_id):
    conversations = normalize_traces(conversations)
    instances = []
    for conv in conversations:
        instances.extend(detect_failures(conv))
    clusters = prioritize(find_patterns(instances, batch_id=batch_id))
    return clusters, conversations


def build_evidence_index(conversations):
    return {c["conversation_id"]: c for c in conversations}


def build_agent_1_3_artifact(before_clusters, after_clusters, before, after):
    """Versioned handoff for anything downstream of detection/clustering --
    the same clusters/evidence as results_*.json, bundled with a schema
    version and producer stage list so a consumer can validate what
    produced it instead of assuming the shape never changes."""
    return {
        "artifact_type": "xray.agent_1_3_output",
        "schema_version": 1,
        "producer_stages": ["trace_investigator", "failure_detective", "pattern_hunter"],
        "batches": {
            "before": {
                "batch_id": "before",
                "total_conversations": len(before),
                "clusters": before_clusters,
                "conversations_by_id": build_evidence_index(before),
            },
            "after": {
                "batch_id": "after",
                "total_conversations": len(after),
                "clusters": after_clusters,
            },
        },
    }


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    before_raw = json.loads((DATA_DIR / "conversations_before.json").read_text())
    after_raw = json.loads((DATA_DIR / "conversations_after.json").read_text())

    clusters_before, before = process_batch(before_raw, batch_id="before")
    clusters_after, after = process_batch(after_raw, batch_id="after")

    evidence_before = build_evidence_index(before)

    (RESULTS_DIR / "results_before.json").write_text(json.dumps({
        "clusters": clusters_before,
        "conversations_by_id": evidence_before,
        "total_conversations": len(before),
    }, indent=2))

    (RESULTS_DIR / "results_after.json").write_text(json.dumps({
        "clusters": clusters_after,
        "total_conversations": len(after),
    }, indent=2))

    if clusters_before:
        top_failure_type = clusters_before[0]["failure_type"]
        probe_result = generate_and_run_probes(top_failure_type, n=5)
        before_freq = clusters_before[0]["frequency"]
        after_match = next((c for c in clusters_after if c["failure_type"] == top_failure_type), None)
        after_freq = after_match["frequency"] if after_match else 0

        (RESULTS_DIR / "regression_probes.json").write_text(json.dumps({
            "cluster_id": clusters_before[0]["cluster_id"],
            "batch_id": "before",
            "top_failure_type": top_failure_type,
            "top_cluster_label": clusters_before[0]["label"],
            "frequency_before_fix": before_freq,
            "frequency_after_fix": after_freq,
            "pass_rate": probe_result["pass_rate"],
            "probes": [
                {"conversation_id": p["conversation_id"], "caught": p["caught"]}
                for p in probe_result["probes"]
            ],
        }, indent=2))

    report = build_executive_report(clusters_before, len(before))
    (RESULTS_DIR / "executive_report.json").write_text(json.dumps(report, indent=2))
    (RESULTS_DIR / "executive_report.md").write_text(render_markdown(report))

    artifact = build_agent_1_3_artifact(clusters_before, clusters_after, before, after)
    (RESULTS_DIR / "agent_1_3_output.json").write_text(json.dumps(artifact, indent=2))

    print(f"before: {len(before)} conversations -> {len(clusters_before)} clusters")
    print(f"after:  {len(after)} conversations -> {len(clusters_after)} clusters")
    if clusters_before:
        print(f"top cluster: {clusters_before[0]['label']} "
              f"(score={clusters_before[0]['priority_score']})")


if __name__ == "__main__":
    main()
