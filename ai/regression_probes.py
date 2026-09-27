"""Closing the loop: for the single highest-priority cluster, generate a
small regression-test suite of new synthetic conversations that would
trigger the same failure pattern, run detection on them, and report the
pass rate -- proof the detector actually catches this bug class, not just
a description of it.
"""

import random

from data.generate_conversations import (
    gen_context_collapse,
    gen_hallucinated_tool_result,
    gen_no_progress_search_loop,
    gen_retry_loop_duplicate_order,
    gen_silent_tool_failure,
    gen_user_frustration,
    gen_wrong_tool_or_target,
)
from ai.failure_detective import detect_failures

GENERATORS = {
    "retry_loop_duplicate_order": lambda rng, cid: gen_retry_loop_duplicate_order(rng, cid, fixed=False),
    "silent_tool_failure": gen_silent_tool_failure,
    "hallucinated_tool_result": gen_hallucinated_tool_result,
    "wrong_tool_or_target": gen_wrong_tool_or_target,
    "context_collapse": gen_context_collapse,
    "user_frustration_signal": gen_user_frustration,
    "no_progress_search_loop": gen_no_progress_search_loop,
}


def detect_all(conversation):
    return detect_failures(conversation)


def generate_and_run_probes(failure_type, n=5, seed=999):
    """Generates n fresh conversations that should trigger `failure_type`,
    runs the full detection pipeline on each, and reports whether it was
    caught."""
    generator = GENERATORS.get(failure_type)
    if generator is None:
        return {"failure_type": failure_type, "probes": [], "pass_rate": None}

    rng = random.Random(seed)
    probes = []
    for i in range(n):
        conv = generator(rng, f"probe_{failure_type}_{i:02d}")
        instances = detect_all(conv)
        caught = any(inst["failure_type"] == failure_type for inst in instances)
        probes.append({
            "conversation_id": conv["conversation_id"],
            "conversation": conv,
            "caught": caught,
        })

    pass_rate = sum(p["caught"] for p in probes) / len(probes) if probes else None
    return {"failure_type": failure_type, "probes": probes, "pass_rate": pass_rate}
