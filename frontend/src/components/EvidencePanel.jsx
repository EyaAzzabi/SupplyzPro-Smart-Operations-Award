import Transcript from "./Transcript";

export default function EvidencePanel({ evidence, loading, error }) {
  if (loading) return <p className="muted">Loading evidence…</p>;
  if (error) return <p className="error">Couldn't load evidence: {error}</p>;
  if (!evidence) return <p className="muted">Select a cluster above to see its transcript evidence.</p>;

  return (
    <div className="evidence-panel">
      <h3>{evidence.label}</h3>
      <p className="muted">{evidence.instances.length} instance(s)</p>
      {evidence.instances.map((instance) => (
        <details key={instance.conversation_id} className="evidence-card">
          <summary>
            <strong>{instance.conversation_id}</strong> — {instance.description}
          </summary>
          <Transcript turns={instance.turns} highlightTurnIds={instance.evidence_turn_ids} />
        </details>
      ))}
    </div>
  );
}
