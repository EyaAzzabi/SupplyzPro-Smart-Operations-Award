export default function FixComparison({ data }) {
  if (!data) return null;

  const max = Math.max(data.frequency_before_fix, data.frequency_after_fix, 1);
  const caughtCount = data.probes.filter((p) => p.caught).length;

  return (
    <div className="fix-comparison">
      <h3>Closing the loop: did the fix work?</h3>
      <p className="muted">
        "{data.top_cluster_label}" — we generated {data.probes.length} new synthetic conversations
        designed to trigger this failure, confirmed the detector still catches them, then re-ran
        detection on a batch where the underlying bug (no idempotency check on retries) was patched.
      </p>

      <div className="bars">
        <div className="bar-row">
          <span className="bar-label">Before fix</span>
          <div className="bar-track">
            <div
              className="bar-fill before"
              style={{ width: `${(data.frequency_before_fix / max) * 100}%` }}
            />
          </div>
          <span className="bar-value">{data.frequency_before_fix}</span>
        </div>
        <div className="bar-row">
          <span className="bar-label">After fix</span>
          <div className="bar-track">
            <div
              className="bar-fill after"
              style={{ width: `${(data.frequency_after_fix / max) * 100}%` }}
            />
          </div>
          <span className="bar-value">{data.frequency_after_fix}</span>
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric">
          <span className="metric-value">{caughtCount}/{data.probes.length}</span>
          <span className="metric-label">regression probes caught</span>
        </div>
        <div className="metric">
          <span className="metric-value">{Math.round(data.pass_rate * 100)}%</span>
          <span className="metric-label">detector catch rate</span>
        </div>
      </div>
    </div>
  );
}
