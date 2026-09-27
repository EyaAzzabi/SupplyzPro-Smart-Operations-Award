"""Operational impact assessment for a cluster.

Deterministic metrics computed from the cluster's own data (frequency,
workflows touched) plus a template-based description of what that failure
type risks operationally. We deliberately separate observed impact (what
the data shows) from potential impact (what this failure type risks if
unaddressed) and never invent a number -- no fabricated dollar amounts or
percentages not backed by the dataset itself.
"""

POTENTIAL_IMPACT = {
    "retry_loop_duplicate_order": [
        "Duplicate real-world purchase orders -- risk of double-shipping and inventory overcommitment.",
        "Unnecessary spend if the duplicate order is fulfilled before being caught.",
    ],
    "silent_tool_failure": [
        "Customer or downstream system receives false confirmation of an action that did not happen.",
        "Errors go untracked, so the same failure can recur silently and repeatedly.",
    ],
    "hallucinated_tool_result": [
        "Business decisions (restocking, order confirmation) made on fabricated data.",
        "Erodes trust in the agent once a customer discovers the discrepancy.",
    ],
    "wrong_tool_or_target": [
        "Information or actions applied to the wrong customer/supplier/order record.",
        "Potential data-privacy exposure if one party's data is surfaced to another.",
    ],
    "context_collapse": [
        "Order fulfilled against terms the user did not actually agree to (e.g. wrong warehouse).",
        "Requires manual correction once discovered, adding operational overhead.",
    ],
    "no_progress_search_loop": [
        "Wasted tool-call cost and latency with no resolution for the user.",
        "User-facing delay that can itself become a frustration signal.",
    ],
    "user_frustration_signal": [
        "Degraded user experience even when the task eventually completes.",
        "Repeated unresolved friction may correlate with support escalations or churn.",
    ],
}


def assess_impact(cluster):
    """`cluster` is one entry from ai/cluster.py's cluster_instances() output
    (already carries frequency, severity, blast_radius, workflows_touched)."""
    failure_type = cluster["failure_type"]
    observed = [
        f"{cluster['frequency']} occurrence(s) detected in the analyzed conversations.",
        f"Touches {cluster['blast_radius']} distinct workflow(s): {', '.join(cluster['workflows_touched'])}.",
    ]
    return {
        "observed_impact": observed,
        "potential_impact": POTENTIAL_IMPACT.get(failure_type, ["Not available -- failure type outside the known taxonomy."]),
        "metrics": {
            "frequency": cluster["frequency"],
            "severity": cluster["severity"],
            "blast_radius": cluster["blast_radius"],
            "priority_score": cluster["priority_score"],
        },
    }
