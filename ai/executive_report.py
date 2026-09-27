"""Assembles clusters + root-cause + impact + remediation into one
dataset-level executive report (structured JSON and human-readable
Markdown). Every conclusion in the report traces back to a cluster and
its evidence -- this is assembly of already-computed structured facts,
not LLM-generated prose, so there's nothing here to hallucinate.
"""

from ai.impact import assess_impact
from ai.remediation import recommend_remediation
from ai.root_cause import analyze_root_cause


def build_cluster_analysis(cluster):
    return {
        "cluster_id": cluster["cluster_id"],
        "label": cluster["label"],
        "failure_type": cluster["failure_type"],
        "priority_score": cluster["priority_score"],
        "root_cause": analyze_root_cause(cluster["failure_type"]),
        "impact": assess_impact(cluster),
        "remediation": recommend_remediation(cluster["failure_type"]),
    }


def build_executive_report(clusters, total_conversations):
    analyses = [build_cluster_analysis(c) for c in clusters]
    total_failures = sum(c["frequency"] for c in clusters)

    return {
        "summary": {
            "total_conversations": total_conversations,
            "total_failures_detected": total_failures,
            "cluster_count": len(clusters),
            "top_priority_cluster": analyses[0]["label"] if analyses else None,
        },
        "clusters": analyses,
    }


def _confidence_note(confidence):
    return {
        "observed": "directly observed in the data",
        "strongly_supported": "strongly supported by the evidence pattern",
        "likely": "the likely explanation, though not certain",
        "possible": "a possible explanation, not confirmable from this data alone",
        "unknown": "not determinable from available data",
    }.get(confidence, confidence)


def render_markdown(report):
    lines = ["# X-Ray Executive Report", ""]
    s = report["summary"]
    lines.append(
        f"Analyzed **{s['total_conversations']}** conversations and found **{s['total_failures_detected']}** "
        f"failures across **{s['cluster_count']}** root-cause clusters."
    )
    if s["top_priority_cluster"]:
        lines.append(f"Top priority: **{s['top_priority_cluster']}**.")
    lines.append("")

    for c in report["clusters"]:
        lines.append(f"## {c['label']} (priority score {c['priority_score']})")
        lines.append("")
        rc = c["root_cause"]
        lines.append(f"**Root cause** ({_confidence_note(rc['confidence'])}): {rc['root_cause']}")
        lines.append("")
        lines.append("Causal chain:")
        for step in rc["causal_chain"]:
            lines.append(f"- *{step['stage'].replace('_', ' ')}*: {step['description']}")
        lines.append("")

        impact = c["impact"]
        lines.append("**Observed impact:**")
        for item in impact["observed_impact"]:
            lines.append(f"- {item}")
        lines.append("**Potential impact:**")
        for item in impact["potential_impact"]:
            lines.append(f"- {item}")
        lines.append("")

        lines.append("**Recommended fixes:**")
        for r in c["remediation"]:
            lines.append(f"- [{r['layer']}, {r['priority']} priority] {r['recommendation']}")
        lines.append("")

    return "\n".join(lines)
