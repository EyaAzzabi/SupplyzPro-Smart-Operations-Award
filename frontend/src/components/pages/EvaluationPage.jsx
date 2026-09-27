import { useEffect, useState } from "react";
import { api } from "../../api";
import { SkeletonBlock, SkeletonCard } from "../SkeletonLoader";
import "../StatsCards.css";
import "../Dashboard.css";
import "./EvaluationPage.css";

function pct(value) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "—";
}

function MetricCard({ label, value, hint, tone = "neutral" }) {
  return (
    <article className={`stats-card stats-card--${tone}`}>
      <div className="stats-card-top">
        <p className="stats-card-label">{label}</p>
      </div>
      <p className="stats-card-value">{value}</p>
      {hint && <p className="stats-card-hint">{hint}</p>}
    </article>
  );
}

export default function EvaluationPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .evaluation()
      .then((res) => {
        if (active) setData(res);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return <p className="error">Couldn't reach the API: {error}. Is the backend running?</p>;
  }

  if (loading) {
    return (
      <div className="fade-in" role="status" aria-busy="true">
        <div className="stats-grid">
          <SkeletonCard height={110} />
          <SkeletonCard height={110} />
          <SkeletonCard height={110} />
          <SkeletonCard height={110} />
        </div>
        <div style={{ marginTop: "1.5rem" }}>
          <SkeletonBlock height={180} radius={12} />
        </div>
      </div>
    );
  }

  const s = data?.synthetic;
  const rw = data?.real_world;

  return (
    <div className="fade-in eval-page">
      <section>
        <h2 className="eval-section-title">Synthetic dataset — ground-truth precision/recall</h2>
        <p className="eval-section-sub">
          Scored against known-answer labels in the seeded dataset ({s?.analysis_latency?.conversations_analyzed} conversations).
        </p>
        <div className="stats-grid">
          <MetricCard
            label="Failure detection"
            value={`${pct(s?.failure_detection_precision_recall?.precision)} / ${pct(s?.failure_detection_precision_recall?.recall)}`}
            hint={`precision / recall — TP ${s?.failure_detection_precision_recall?.tp}, FP ${s?.failure_detection_precision_recall?.fp}, FN ${s?.failure_detection_precision_recall?.fn}`}
            tone="success"
          />
          <MetricCard
            label="Cluster grouping"
            value={`${pct(s?.cluster_precision_recall?.precision)} / ${pct(s?.cluster_precision_recall?.recall)}`}
            hint="precision / recall (pairwise)"
            tone="success"
          />
          <MetricCard
            label="Root-cause accuracy"
            value={pct(s?.root_cause_accuracy?.accuracy)}
            hint={`n = ${s?.root_cause_accuracy?.n} detected failures`}
            tone="success"
          />
          <MetricCard
            label="Silent-failure recall"
            value={pct(s?.silent_failure_recall?.recall)}
            hint={`n = ${s?.silent_failure_recall?.n}`}
            tone="success"
          />
        </div>
        <div className="eval-meta-row">
          <div className="eval-meta-card">
            <p className="eval-meta-label">Analysis latency</p>
            <p className="eval-meta-value">{s?.analysis_latency?.total_seconds?.toFixed(2)}s total</p>
            <p className="eval-meta-sub">
              detection {s?.analysis_latency?.detection_seconds?.toFixed(4)}s · clustering{" "}
              {s?.analysis_latency?.clustering_seconds?.toFixed(2)}s
            </p>
          </div>
          <div className="eval-meta-card">
            <p className="eval-meta-label">Cost per analysis</p>
            <p className="eval-meta-value">${s?.cost_per_analysis?.estimated_cost_usd?.toFixed(2)}</p>
            <p className="eval-meta-sub">{s?.cost_per_analysis?.mode}</p>
          </div>
        </div>
      </section>

      {rw && (
        <section style={{ marginTop: "2rem" }}>
          <h2 className="eval-section-title">Real-world validation — tau-bench (Sierra Research)</h2>
          <p className="eval-section-sub">
            {rw.dataset}. Scored against real task-completion outcomes, not our own labels — a genuinely
            harder, honest test.
          </p>
          <div className="eval-domain-grid">
            <div className="eval-domain-card">
              <p className="eval-domain-title">Overall</p>
              <p className="eval-domain-stat">
                {pct(rw.overall.recall_on_genuine_failures)} <span>recall</span>
              </p>
              <p className="eval-domain-stat">
                {pct(rw.overall.false_positive_rate_on_genuine_successes)} <span>false-positive rate</span>
              </p>
              <p className="eval-domain-sub">
                {rw.overall.n} conversations ({rw.overall.n_failed} failed, {rw.overall.n_succeeded} succeeded)
              </p>
            </div>
            {Object.entries(rw.by_domain).map(([domain, m]) => (
              <div className="eval-domain-card" key={domain}>
                <p className="eval-domain-title">{domain.replace(/_/g, " ")}</p>
                <p className="eval-domain-stat">
                  {pct(m.recall_on_genuine_failures)} <span>recall</span>
                </p>
                <p className="eval-domain-stat">
                  {pct(m.false_positive_rate_on_genuine_successes)} <span>false-positive rate</span>
                </p>
                <p className="eval-domain-sub">
                  {m.n} conversations ({m.n_failed} failed, {m.n_succeeded} succeeded)
                </p>
              </div>
            ))}
          </div>
          <details className="eval-note">
            <summary>Why this is lower than the synthetic score, honestly</summary>
            <p>{rw.note}</p>
          </details>
        </section>
      )}
    </div>
  );
}
