"""X-Ray -- Finding the Hidden Failures in SupplyzPro agent conversations.

Streamlit dashboard: ranked failure clusters -> drill into real transcript
evidence -> for the top-priority cluster, proof that a fix works (before/
after frequency + a regression-probe pass rate).

Run: streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
RESULTS_DIR = ROOT / "results"

st.set_page_config(page_title="X-Ray", page_icon="🩻", layout="wide")


@st.cache_data
def load_results():
    before = json.loads((RESULTS_DIR / "results_before.json").read_text())
    after = json.loads((RESULTS_DIR / "results_after.json").read_text())
    probes_path = RESULTS_DIR / "regression_probes.json"
    probes = json.loads(probes_path.read_text()) if probes_path.exists() else None
    return before, after, probes


def render_transcript(conversation, highlight_turn_ids):
    for turn in conversation["turns"]:
        is_evidence = turn["turn_id"] in highlight_turn_ids
        prefix = "🟥" if is_evidence else "⬜"
        role = turn["role"].upper()
        st.markdown(f"{prefix} **{role}** (turn {turn['turn_id']}): {turn['text']}")
        if "tool_call" in turn:
            call = turn["tool_call"]
            with st.container():
                st.code(
                    f"tool: {call['tool_name']}\n"
                    f"parameters: {json.dumps(call['parameters'])}\n"
                    f"response: {json.dumps(call.get('response'))}\n"
                    f"error_code: {call.get('error_code')}   latency_ms: {call.get('latency_ms')}",
                    language="text",
                )


def main():
    st.title("🩻 X-Ray")
    st.caption(
        "We don't just find bugs in AI-agent conversations — we group them by root cause, "
        "rank them by real impact, and prove a fix works."
    )

    before, after, probes = load_results()
    clusters = before["clusters"]
    conversations_by_id = before["conversations_by_id"]

    st.info(
        f"Analyzed **{before['total_conversations']}** synthetic SupplyzPro agent conversations "
        f"(inventory checks, purchase orders, supplier lookups, shipment tracking) and found "
        f"**{sum(c['frequency'] for c in clusters)}** hidden failures across **{len(clusters)}** "
        f"root-cause clusters."
    )

    st.subheader("Failure clusters, ranked by Priority Score = Frequency × Severity × Blast Radius")
    table = pd.DataFrame([
        {
            "Cluster": c["label"],
            "Frequency": c["frequency"],
            "Severity": c["severity"],
            "Blast Radius": c["blast_radius"],
            "Priority Score": c["priority_score"],
            "Workflows touched": ", ".join(c["workflows_touched"]),
        }
        for c in clusters
    ])
    st.dataframe(table, hide_index=True, use_container_width=True)

    st.subheader("Evidence")
    labels = [c["label"] for c in clusters]
    selected_label = st.selectbox("Drill into a cluster's real transcript evidence:", labels)
    selected_cluster = next(c for c in clusters if c["label"] == selected_label)

    st.caption(
        f"{selected_cluster['frequency']} instance(s) across "
        f"{', '.join(selected_cluster['workflows_touched'])}."
    )
    for instance in selected_cluster["instances"]:
        with st.expander(f"{instance['conversation_id']} — {instance['description']}"):
            conv = conversations_by_id[instance["conversation_id"]]
            render_transcript(conv, set(instance["evidence_turn_ids"]))

    if probes:
        st.subheader("Closing the loop: did the fix work?")
        col1, col2, col3 = st.columns(3)
        col1.metric(
            f"'{probes['top_cluster_label']}' — before fix",
            probes["frequency_before_fix"],
        )
        col2.metric(
            f"'{probes['top_cluster_label']}' — after fix",
            probes["frequency_after_fix"],
            delta=probes["frequency_after_fix"] - probes["frequency_before_fix"],
        )
        col3.metric(
            "Regression-probe catch rate",
            f"{probes['pass_rate'] * 100:.0f}%" if probes["pass_rate"] is not None else "n/a",
        )
        st.caption(
            f"We generated {len(probes['probes'])} new synthetic conversations designed to "
            f"trigger '{probes['top_cluster_label']}' and confirmed the detector still catches "
            f"them — then re-ran the same detection pipeline on a batch of conversations where "
            f"the underlying bug was patched (an idempotency key on the order-creation call) to "
            f"confirm the cluster actually shrinks, not just that we assume the fix worked."
        )

    with st.expander("How this works / AI tools disclosed"):
        st.markdown(
            "- **Rule-based layer**: explicit error codes, timeouts, and identical repeated "
            "tool calls.\n"
            "- **LLM-as-judge layer**: compares each tool call's raw response against the "
            "agent's next message to catch hallucinated claims and wrong-target tool calls. "
            "Uses an NVIDIA NIM-hosted LLM when `NVIDIA_API_KEY` is set (see `.env.example`); "
            "falls back to a deterministic offline heuristic otherwise, so the pipeline is "
            "fully reproducible without a live API key.\n"
            "- **Behavioral layer**: flags dropped constraints (context collapse) and repeated "
            "user rephrasing (frustration signal).\n"
            "- **Clustering**: TF-IDF + KMeans over each failure's natural-language description, "
            "grouping by root cause rather than by surface symptom.\n"
            "- All data on this dashboard is **synthetic**, generated by `data/generate_conversations.py` "
            "to represent plausible SupplyzPro workflows.\n"
            "- **NVIDIA Brev: not used** — no GPU compute was required; the LLM-as-judge calls hosted "
            "inference (NIM) rather than running a model locally."
        )


if __name__ == "__main__":
    main()
