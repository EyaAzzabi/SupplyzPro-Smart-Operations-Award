"""Pulls a real-world validation set from tau-bench (Sierra Research, MIT
license) -- actual GPT-4o agent transcripts across two domains (retail
customer service, airline booking/support), with real tool calls and a
task `reward` (1.0 = genuinely succeeded, 0.0 = genuinely failed) as
ground truth.

This exists to answer a fair question: does the detector only work on
failure patterns we hand-crafted ourselves? Running it against a public
dataset we didn't design is a real test, not a self-graded one. Two
domains (not one) also tests whether findings generalize or are an
artifact of one domain's tool/response shapes. We use `reward` as coarse
ground truth (did the task fail at all), not our detailed root-cause
taxonomy -- tau-bench doesn't label *why* a task failed the way our
synthetic data does, so root-cause accuracy can't be scored on this set,
only detection recall/false-positive rate.

Source: https://github.com/sierra-research/tau-bench (MIT license)
        historical_trajectories/gpt-4o-{retail,airline}.json

Run: python data/fetch_real_world_sample.py
"""

import json
import random
import urllib.request
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/sierra-research/tau-bench/main/historical_trajectories"
DOMAINS = [
    {"name": "retail", "file": "gpt-4o-retail.json", "workflow": "retail_customer_service"},
    {"name": "airline", "file": "gpt-4o-airline.json", "workflow": "airline_booking_support"},
]
OUT_DIR = Path(__file__).parent
MAX_MESSAGES = 20  # keep each sample readable in the dashboard
SAMPLE_PER_CLASS = 20  # per domain, per (failed/succeeded) class


def convert_trajectory(conv_id, workflow, reward, traj):
    turns = []
    pending = {}  # tool_call_id -> the turn dict awaiting its response
    turn_id = 0

    for msg in traj:
        role = msg.get("role")
        if role == "system":
            continue

        if role == "user":
            turn_id += 1
            turns.append({"turn_id": turn_id, "role": "user", "text": msg.get("content") or ""})

        elif role == "assistant":
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                turn_id += 1
                turns.append({"turn_id": turn_id, "role": "agent", "text": content})
                continue
            for tc in tool_calls:
                turn_id += 1
                fn = tc["function"]
                try:
                    params = json.loads(fn["arguments"])
                except (json.JSONDecodeError, TypeError):
                    params = {"raw_arguments": fn["arguments"]}
                turn = {
                    "turn_id": turn_id, "role": "agent", "text": content,
                    "tool_call": {
                        "tool_name": fn["name"], "parameters": params,
                        "response": None, "latency_ms": None, "error_code": None,
                    },
                }
                turns.append(turn)
                pending[tc["id"]] = turn

        elif role == "tool":
            turn = pending.get(msg.get("tool_call_id"))
            if turn is None:
                continue
            raw = msg.get("content") or ""
            try:
                response = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                response = {"text": raw}
            turn["tool_call"]["response"] = response
            if isinstance(raw, str) and raw.lower().startswith("error"):
                turn["tool_call"]["error_code"] = "tool_error"

    return {
        "conversation_id": conv_id,
        "workflow": workflow,
        "failure_type": None,  # no per-instance root-cause label in tau-bench; use task_reward
        "source": "tau-bench (Sierra Research, MIT license)",
        "task_reward": reward,
        "turns": turns,
    }


def sample_domain(domain, rng):
    url = f"{BASE_URL}/{domain['file']}"
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url, timeout=60) as resp:
        raw_trajectories = json.loads(resp.read())
    print(f"  loaded {len(raw_trajectories)} {domain['name']} trajectories.")

    short_enough = [t for t in raw_trajectories if len(t["traj"]) <= MAX_MESSAGES]
    failed = [t for t in short_enough if t["reward"] < 1.0]
    succeeded = [t for t in short_enough if t["reward"] == 1.0]
    rng.shuffle(failed)
    rng.shuffle(succeeded)
    sampled = failed[:SAMPLE_PER_CLASS] + succeeded[:SAMPLE_PER_CLASS]

    return [
        convert_trajectory(f"tau_{domain['name']}_{i:03d}", domain["workflow"], t["reward"], t["traj"])
        for i, t in enumerate(sampled)
    ]


def main():
    rng = random.Random(7)
    conversations = []
    for domain in DOMAINS:
        conversations.extend(sample_domain(domain, rng))
    rng.shuffle(conversations)

    out_path = OUT_DIR / "conversations_real_world.json"
    out_path.write_text(json.dumps(conversations, indent=2))

    by_domain = {}
    for c in conversations:
        d = by_domain.setdefault(c["workflow"], {"failed": 0, "succeeded": 0})
        d["failed" if c["task_reward"] < 1.0 else "succeeded"] += 1

    print(f"\nWrote {len(conversations)} real-world conversations to {out_path}:")
    for workflow, counts in by_domain.items():
        print(f"  {workflow}: {counts['failed']} genuinely failed, {counts['succeeded']} genuinely succeeded")


if __name__ == "__main__":
    main()
