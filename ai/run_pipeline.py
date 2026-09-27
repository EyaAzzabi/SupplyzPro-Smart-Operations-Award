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

from ai.behavioral import run_behavioral
from ai.cluster import cluster_instances
from ai.executive_report import build_executive_report, render_markdown
from ai.llm_judge import run_llm_judge
from ai.prioritize import prioritize
from ai.regression_probes import generate_and_run_probes
from ai.rules import run_rule_based

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"


def detect_all(conversation):
    return run_rule_based(conversation) + run_llm_judge(conversation) + run_behavioral(conversation)


def process_batch(conversations):
    instances = []
    for conv in conversations:
        instances.extend(detect_all(conv))
    clusters = prioritize(cluster_instances(instances))
    return clusters


def build_evidence_index(conversations):
    return {c["conversation_id"]: c for c in conversations}


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    before = json.loads((DATA_DIR / "conversations_before.json").read_text())
    after = json.loads((DATA_DIR / "conversations_after.json").read_text())

    clusters_before = process_batch(before)
    clusters_after = process_batch(after)

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

    print(f"before: {len(before)} conversations -> {len(clusters_before)} clusters")
    print(f"after:  {len(after)} conversations -> {len(clusters_after)} clusters")
    if clusters_before:
        print(f"top cluster: {clusters_before[0]['label']} "
              f"(score={clusters_before[0]['priority_score']})")


if __name__ == "__main__":
    main()
