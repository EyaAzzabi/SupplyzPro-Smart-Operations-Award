export default function ClusterAnalysis({ analysis, loading, error }) {
  if (loading) return <p className="muted">Loading analysis…</p>;
  if (error) return <p className="error">Couldn't load analysis: {error}</p>;
  if (!analysis) return null;

  const { root_cause: rc, impact, remediation } = analysis;

  return (
    <div className="cluster-analysis">
      <div className="analysis-grid">
        <div>
          <h4>Root cause ({rc.confidence.replace("_", " ")})</h4>
          <p>{rc.root_cause}</p>
          <ul>
            {rc.causal_chain.map((step) => (
              <li key={step.stage}>
                <em>{step.stage.replace(/_/g, " ")}</em>: {step.description}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Impact</h4>
          <p className="muted">Observed:</p>
          <ul>
            {impact.observed_impact.map((item, i) => <li key={i}>{item}</li>)}
          </ul>
          <p className="muted">Potential:</p>
          <ul>
            {impact.potential_impact.map((item, i) => <li key={i}>{item}</li>)}
          </ul>
        </div>
      </div>
      <h4>Recommended fixes</h4>
      <ul>
        {remediation.map((r, i) => (
          <li key={i}>
            <code>{r.layer}</code> ({r.priority} priority): {r.recommendation}
          </li>
        ))}
      </ul>
    </div>
  );
}
