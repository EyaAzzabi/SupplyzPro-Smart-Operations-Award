"""Runs the detector against the real-world tau-bench sample
(data/conversations_real_world.json) and scores it against `task_reward`
(1.0 = the agent genuinely completed the task correctly, <1.0 = it
genuinely failed, per tau-bench's own grader -- not our label).

This is deliberately a harder, honest test: tau-bench is a different
domain (retail returns/exchanges, not supply-chain ops) with different
tool names and response shapes than our synthetic data. We do NOT expect
scores as high as the synthetic evaluation -- the point of this script is
to report what actually happens on data we didn't design for our own
detector, not to reproduce a clean number.

Run: python -m evaluation.run_real_world_evaluation
"""

import json
from pathlib import Path

from ai.behavioral import run_behavioral
from ai.llm_judge import run_llm_judge
from ai.rules import run_rule_based

ROOT = Path(__file__).parent.parent
RESULTS_DIR = Path(__file__).parent / "results"


def detect_all(conversation):
    return run_rule_based(conversation) + run_llm_judge(conversation) + run_behavioral(conversation)


def main():
    conversations = json.loads((ROOT / "data" / "conversations_real_world.json").read_text())

    rows = []
    for conv in conversations:
        instances = detect_all(conv)
        rows.append({
            "conversation_id": conv["conversation_id"],
            "task_reward": conv["task_reward"],
            "genuinely_failed": conv["task_reward"] < 1.0,
            "flagged": len(instances) > 0,
            "flagged_types": sorted(set(i["failure_type"] for i in instances)),
        })

    failed = [r for r in rows if r["genuinely_failed"]]
    succeeded = [r for r in rows if not r["genuinely_failed"]]

    recall = sum(r["flagged"] for r in failed) / len(failed) if failed else None
    false_positive_rate = sum(r["flagged"] for r in succeeded) / len(succeeded) if succeeded else None

    type_counts = {}
    for r in rows:
        for t in r["flagged_types"]:
            type_counts[t] = type_counts.get(t, 0) + 1

    metrics = {
        "dataset": "tau-bench gpt-4o-retail sample (30 conversations: 15 genuinely failed, 15 genuinely succeeded)",
        "recall_on_genuine_failures": recall,
        "false_positive_rate_on_genuine_successes": false_positive_rate,
        "flagged_failure_type_counts": type_counts,
        "note": (
            "Lower than the synthetic evaluation's 1.00/1.00 by design, for two honest reasons, not "
            "one. (1) Domain mismatch: tau-bench uses different tool names and response schemas than "
            "our supply-chain domain, so the domain-specific hallucination heuristic in "
            "ai/llm_judge.py's offline fallback mostly doesn't engage here (it looks for a 'quantity' "
            "field this dataset's tools don't return) -- only the domain-agnostic rule-based and "
            "behavioral layers meaningfully transfer without modification. (2) A more fundamental "
            "point: tau-bench's `reward` measures whether the task was completed correctly, not "
            "whether the agent was deceptive. Several reward=0 conversations are the agent honestly "
            "telling the user it's stuck (e.g. asking for an order ID it never receives, then saying "
            "so) -- a genuinely incomplete task, but not a hidden failure in our sense, and our "
            "detector is correct to stay quiet on those. Recall against raw `reward` therefore "
            "understates precision on the failure mode we actually target: confident, wrong claims."
        ),
        "conversations": rows,
    }

    (RESULTS_DIR / "real_world_metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"Recall on genuine failures: {recall}")
    print(f"False positive rate on genuine successes: {false_positive_rate}")
    print(f"Flagged failure type counts: {type_counts}")


if __name__ == "__main__":
    main()
