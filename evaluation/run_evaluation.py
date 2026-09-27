"""Computes the required evaluation metrics against the synthetic ground
truth and writes evaluation/results/metrics.json + metrics.md.

Ground truth comes from data/conversations_before.json: every synthetic
conversation is labeled with the failure_type it was generated to contain
(or None for normal/legitimate-retry/recovery conversations). This lets us
score precision/recall honestly instead of asserting it.

Run: python -m evaluation.run_evaluation
"""

import itertools
import json
import time
from pathlib import Path

from ai.cluster import cluster_instances
from ai.failure_detective import detect_failures
from ai.prioritize import prioritize

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = Path(__file__).parent / "results"


def detect_all(conversation):
    return detect_failures(conversation)


def failure_detection_precision_recall(conversations, instances_by_conv):
    """Conversation-level: did we flag *something* in every conversation
    that actually contains a seeded failure, and stay quiet on the ones
    that don't (normal conversations, legitimate retries, recoveries)?"""
    tp = fp = fn = 0
    for conv in conversations:
        has_failure = conv["failure_type"] is not None
        was_flagged = len(instances_by_conv.get(conv["conversation_id"], [])) > 0
        if has_failure and was_flagged:
            tp += 1
        elif has_failure and not was_flagged:
            fn += 1
        elif not has_failure and was_flagged:
            fp += 1
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return {"precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn}


def cluster_pairwise_precision_recall(clusters):
    """Pairwise clustering quality: of all pairs of detected instances put
    in the same cluster, how many actually share the same true failure
    type (precision)? Of all pairs that truly share a failure type, how
    many did we put in the same cluster (recall)?"""
    all_instances = [inst for c in clusters for inst in c["instances"]]
    cluster_of = {}
    for c in clusters:
        for inst in c["instances"]:
            cluster_of[id(inst)] = c["cluster_id"]

    same_cluster_pairs = 0
    same_cluster_and_same_type = 0
    same_type_pairs = 0
    same_type_and_same_cluster = 0

    for a, b in itertools.combinations(all_instances, 2):
        same_type = a["failure_type"] == b["failure_type"]
        same_cluster = cluster_of[id(a)] == cluster_of[id(b)]
        if same_cluster:
            same_cluster_pairs += 1
            if same_type:
                same_cluster_and_same_type += 1
        if same_type:
            same_type_pairs += 1
            if same_cluster:
                same_type_and_same_cluster += 1

    precision = same_cluster_and_same_type / same_cluster_pairs if same_cluster_pairs else None
    recall = same_type_and_same_cluster / same_type_pairs if same_type_pairs else None
    return {"precision": precision, "recall": recall}


def root_cause_accuracy(clusters):
    """Of every detected instance, does its own true failure_type match
    the dominant (majority-vote) label of the cluster it landed in?"""
    correct = total = 0
    for c in clusters:
        for inst in c["instances"]:
            total += 1
            if inst["failure_type"] == c["failure_type"]:
                correct += 1
    return {"accuracy": correct / total if total else None, "n": total}


def silent_failure_recall(conversations, instances_by_conv):
    silent_convs = [c for c in conversations if c["failure_type"] == "silent_tool_failure"]
    caught = sum(
        1 for c in silent_convs
        if any(i["failure_type"] == "silent_tool_failure" for i in instances_by_conv.get(c["conversation_id"], []))
    )
    return {"recall": caught / len(silent_convs) if silent_convs else None, "n": len(silent_convs)}


def measure_latency(conversations):
    """Ingestion+detection, clustering, and prioritization ("explanation"),
    timed separately over the full before-batch."""
    t0 = time.perf_counter()
    instances = []
    for conv in conversations:
        instances.extend(detect_all(conv))
    t1 = time.perf_counter()

    clusters = cluster_instances(instances)
    t2 = time.perf_counter()

    prioritize(clusters)
    t3 = time.perf_counter()

    return {
        "detection_seconds": round(t1 - t0, 4),
        "clustering_seconds": round(t2 - t1, 4),
        "prioritization_seconds": round(t3 - t2, 4),
        "total_seconds": round(t3 - t0, 4),
        "conversations_analyzed": len(conversations),
    }, instances, clusters


def estimate_cost(conversations, using_live_nvidia_nim):
    tool_call_count = sum(1 for c in conversations for t in c["turns"] if "tool_call" in t)
    if not using_live_nvidia_nim:
        return {
            "mode": "local-only (offline heuristic judge, no API calls)",
            "llm_calls": 0,
            "estimated_cost_usd": 0.0,
        }
    # ~150 input tokens + ~60 output tokens per judged tool call, rough estimate.
    est_tokens = tool_call_count * 210
    return {
        "mode": "NVIDIA NIM (build.nvidia.com hosted inference)",
        "llm_calls": tool_call_count,
        "estimated_tokens": est_tokens,
        "estimated_cost_usd": "free tier during hackathon; see build.nvidia.com pricing for sustained use",
    }


def main():
    import os

    RESULTS_DIR.mkdir(exist_ok=True)
    conversations = json.loads((DATA_DIR / "conversations_before.json").read_text())

    latency, instances, raw_clusters = measure_latency(conversations)
    clusters = prioritize(cluster_instances(instances))

    instances_by_conv = {}
    for inst in instances:
        instances_by_conv.setdefault(inst["conversation_id"], []).append(inst)

    metrics = {
        "failure_detection_precision_recall": failure_detection_precision_recall(conversations, instances_by_conv),
        "cluster_precision_recall": cluster_pairwise_precision_recall(clusters),
        "root_cause_accuracy": root_cause_accuracy(clusters),
        "silent_failure_recall": silent_failure_recall(conversations, instances_by_conv),
        "analysis_latency": latency,
        "cost_per_analysis": estimate_cost(conversations, using_live_nvidia_nim=bool(os.environ.get("NVIDIA_API_KEY"))),
    }

    (RESULTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    lines = ["# Evaluation results", "", "Computed against synthetic ground truth in `data/conversations_before.json` "
             f"({len(conversations)} conversations).", ""]
    dpr = metrics["failure_detection_precision_recall"]
    lines.append(f"- **Failure detection precision/recall**: "
                 f"{dpr['precision']:.2f} / {dpr['recall']:.2f} (TP={dpr['tp']}, FP={dpr['fp']}, FN={dpr['fn']})")
    cpr = metrics["cluster_precision_recall"]
    lines.append(f"- **Cluster precision/recall**: {cpr['precision']:.2f} / {cpr['recall']:.2f} (pairwise)")
    rca = metrics["root_cause_accuracy"]
    lines.append(f"- **Root-cause accuracy**: {rca['accuracy']:.2f} (n={rca['n']})")
    sfr = metrics["silent_failure_recall"]
    lines.append(f"- **Silent-failure recall**: {sfr['recall']:.2f} (n={sfr['n']})")
    lat = metrics["analysis_latency"]
    lines.append(f"- **Analysis latency**: detection {lat['detection_seconds']}s, "
                 f"clustering {lat['clustering_seconds']}s, prioritization {lat['prioritization_seconds']}s, "
                 f"total {lat['total_seconds']}s for {lat['conversations_analyzed']} conversations")
    cost = metrics["cost_per_analysis"]
    lines.append(f"- **Cost per analysis**: {cost['mode']}, {cost['llm_calls']} LLM calls, "
                 f"estimated cost {cost['estimated_cost_usd']}")

    (RESULTS_DIR / "metrics.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
