"""Pulls a small, real-world validation set from tau-bench (Sierra Research,
MIT license) -- actual GPT-4o agent transcripts in a retail customer-service
domain, with real tool calls and a task `reward` (1.0 = genuinely succeeded,
0.0 = genuinely failed) as ground truth.

This exists to answer a fair question: does the detector only work on
failure patterns we hand-crafted ourselves? Running it against a public
dataset we didn't design is a real test, not a self-graded one. We use
`reward` as coarse ground truth (did the task fail at all), not our
detailed root-cause taxonomy -- tau-bench doesn't label *why* a task
failed the way our synthetic data does, so root-cause accuracy can't be
scored on this set, only detection recall/false-positive rate.

Source: https://github.com/sierra-research/tau-bench
        historical_trajectories/gpt-4o-retail.json (MIT license)

Run: python data/fetch_real_world_sample.py
"""

import json
import random
import urllib.request
from pathlib import Path

SOURCE_URL = (
    "https://raw.githubusercontent.com/sierra-research/tau-bench/main/"
    "historical_trajectories/gpt-4o-retail.json"
)
OUT_DIR = Path(__file__).parent
MAX_MESSAGES = 20  # keep the sample readable in the dashboard
SAMPLE_PER_CLASS = 15


def convert_trajectory(conv_id, reward, traj):
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
        "workflow": "retail_customer_service",
        "failure_type": None,  # no per-instance root-cause label in tau-bench; use task_reward
        "source": "tau-bench (Sierra Research, MIT license)",
        "task_reward": reward,
        "turns": turns,
    }


def main():
    print(f"Downloading {SOURCE_URL} ...")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        raw_trajectories = json.loads(resp.read())
    print(f"Loaded {len(raw_trajectories)} trajectories.")

    short_enough = [t for t in raw_trajectories if len(t["traj"]) <= MAX_MESSAGES]
    failed = [t for t in short_enough if t["reward"] < 1.0]
    succeeded = [t for t in short_enough if t["reward"] == 1.0]

    rng = random.Random(7)
    rng.shuffle(failed)
    rng.shuffle(succeeded)
    sampled = failed[:SAMPLE_PER_CLASS] + succeeded[:SAMPLE_PER_CLASS]
    rng.shuffle(sampled)

    conversations = [
        convert_trajectory(f"tau_retail_{i:03d}", t["reward"], t["traj"])
        for i, t in enumerate(sampled)
    ]

    out_path = OUT_DIR / "conversations_real_world.json"
    out_path.write_text(json.dumps(conversations, indent=2))
    print(f"Wrote {len(conversations)} real-world conversations to {out_path} "
          f"({sum(1 for c in conversations if c['task_reward'] < 1.0)} genuinely failed, "
          f"{sum(1 for c in conversations if c['task_reward'] == 1.0)} genuinely succeeded).")


if __name__ == "__main__":
    main()
