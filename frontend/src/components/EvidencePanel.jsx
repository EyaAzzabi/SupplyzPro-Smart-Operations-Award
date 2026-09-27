import Transcript from "./Transcript";
import "./EvidencePanel.css";

function WarningIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3.5 2.8 19a1 1 0 0 0 .87 1.5h16.66a1 1 0 0 0 .87-1.5z" />
      <path d="M12 9v4.5M12 16.8v.2" />
    </svg>
  );
}

export default function EvidencePanel({ evidence, loading, error }) {
  if (loading) {
    return (
      <div className="evidence-state" role="status">
        <span className="evidence-spinner" aria-hidden="true" />
        Loading transcript evidence…
      </div>
    );
  }

  if (error) {
    return <p className="error">Couldn't load evidence: {error}</p>;
  }

  if (!evidence) {
    return (
      <div className="evidence-state">
        Select a cluster in the table above to see the real transcripts where it was detected.
      </div>
    );
  }

  const instances = evidence.instances ?? [];

  return (
    <div className="evidence-panel">
      <header className="evidence-header">
        <h3 className="evidence-title">{evidence.label}</h3>
        <p className="evidence-subtitle">
          {instances.length} instance{instances.length === 1 ? "" : "s"} detected in the raw agent
          transcripts — highlighted turns are the evidence itself.
        </p>
      </header>

      <div className="evidence-list">
        {instances.map((instance, index) => (
          <article
            key={instance.conversation_id}
            className="evidence-card"
            style={{ animationDelay: `${Math.min(index, 6) * 60}ms` }}
          >
            <div className="evidence-card-head">
              <span className="evidence-icon" aria-hidden="true">
                <WarningIcon />
              </span>
              <div className="evidence-headings">
                <h4 className="evidence-conv">{instance.conversation_id}</h4>
                <p className="evidence-desc">{instance.description}</p>
              </div>
              <span className="evidence-detector" title={`Detected by ${instance.detector}`}>
                {instance.detector}
              </span>
            </div>

            <Transcript turns={instance.turns} highlightTurnIds={instance.evidence_turn_ids} />
          </article>
        ))}
      </div>
    </div>
  );
}
