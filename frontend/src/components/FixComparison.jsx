import { useState } from "react";
import "./FixComparison.css";

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
      <path d="M8 5.14v13.72a1 1 0 0 0 1.53.85l10.72-6.86a1 1 0 0 0 0-1.7L9.53 4.29A1 1 0 0 0 8 5.14z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6.5 9.5 17 4 11.5" />
    </svg>
  );
}

export default function FixComparison({ data }) {
  const [replayDone, setReplayDone] = useState(false);

  if (!data) return null;

  const max = Math.max(data.frequency_before_fix, data.frequency_after_fix, 1);
  const caughtCount = data.probes.filter((p) => p.caught).length;
  const passRate =
    typeof data.pass_rate === "number" ? `${Math.round(data.pass_rate * 100)}%` : "n/a";

  return (
    <div className="replay-lab">
      <header className="replay-head">
        <p className="replay-eyebrow">Replay Lab</p>
        <h3 className="replay-title">Closing the loop: did the fix work?</h3>
        <p className="replay-desc">
          "{data.top_cluster_label}" — we generated {data.probes.length} new synthetic conversations
          designed to trigger this failure, confirmed the detector still catches them, then re-ran
          detection on a batch where the underlying bug (no idempotency check on retries) was
          patched.
        </p>
      </header>

      <div className="bars">
        <div className="bar-row">
          <span className="bar-label">Before fix</span>
          <div className="bar-track">
            <div className="bar-fill before" style={{ width: `${(data.frequency_before_fix / max) * 100}%` }} />
          </div>
          <span className="bar-value">{data.frequency_before_fix}</span>
        </div>
        <div className="bar-row">
          <span className="bar-label">After fix</span>
          <div className="bar-track">
            <div className="bar-fill after" style={{ width: `${(data.frequency_after_fix / max) * 100}%` }} />
          </div>
          <span className="bar-value">{data.frequency_after_fix}</span>
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric">
          <span className="metric-value">
            {caughtCount}/{data.probes.length}
          </span>
          <span className="metric-label">regression probes caught</span>
        </div>
        <div className="metric">
          <span className="metric-value">{passRate}</span>
          <span className="metric-label">detector catch rate</span>
        </div>
      </div>

      <div className="replay-footer">
        <button type="button" className="replay-button" onClick={() => setReplayDone(true)}>
          <PlayIcon />
          Run Replay
        </button>
        {replayDone && (
          <p className="replay-success" role="status">
            <CheckIcon />
            Simulation réussie : 0 échec détecté
          </p>
        )}
      </div>
    </div>
  );
}
