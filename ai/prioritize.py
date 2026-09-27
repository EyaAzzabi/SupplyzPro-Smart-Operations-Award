"""Priority Score = Frequency x Severity x Blast Radius

A simple, auditable formula on purpose: every number a reviewer sees can
be checked by hand against the underlying instance counts, rather than
trusting a black-box ranking.
"""

SEVERITY = {
    "retry_loop_duplicate_order": 3,   # causes a real-world duplicated action
    "silent_tool_failure": 3,          # silently wrong info reaches the customer
    "hallucinated_tool_result": 3,     # silently wrong info reaches the customer
    "wrong_tool_or_target": 2,         # wrong data used, but no external action taken
    "context_collapse": 2,             # a stated constraint is violated
    "user_frustration_signal": 1,      # inconvenience, no wrong data or action
    "no_progress_search_loop": 2,      # wastes time/cost, no wrong data reaches the user
}


def score_cluster(cluster):
    frequency = cluster["frequency"]
    severity = SEVERITY.get(cluster["failure_type"], 1)
    blast_radius = len(cluster["workflows_touched"])
    cluster["severity"] = severity
    cluster["blast_radius"] = blast_radius
    cluster["priority_score"] = frequency * severity * blast_radius
    return cluster


def prioritize(clusters):
    scored = [score_cluster(c) for c in clusters]
    scored.sort(key=lambda c: c["priority_score"], reverse=True)
    return scored
