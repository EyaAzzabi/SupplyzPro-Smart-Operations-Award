import { useState } from "react";
import EvidencePanel from "../EvidencePanel";
import { SkeletonBlock, SkeletonText } from "../SkeletonLoader";
import { useConversationIndex, useOverview } from "../../hooks/useXrayData";
import "../Dashboard.css";

const SEVERITY_LABEL = { 1: "Low", 2: "Medium", 3: "High" };

export default function TraceExplorerPage() {
  const { clusters, loading, error } = useOverview();
  const { conversations, loading: indexLoading } = useConversationIndex(clusters);
  const [pickedId, setPickedId] = useState(null);

  const activeId = pickedId ?? conversations[0]?.conversation_id ?? null;
  const active = conversations.find((c) => c.conversation_id === activeId) ?? null;

  if (error) {
    return <p className="error">Couldn't reach the API: {error}. Is the backend running?</p>;
  }

  if (loading || indexLoading) {
    return (
      <div className="dash-split fade-in" role="status" aria-busy="true">
        <span className="sr-only">Indexing conversations…</span>
        <section className="trace-index" aria-hidden="true">
          <SkeletonBlock height={14} radius={6} />
          <div style={{ marginTop: "0.9rem", display: "grid", gap: "0.4rem" }}>
            {Array.from({ length: 7 }, (_, index) => (
              <SkeletonBlock key={index} height={62} radius={9} />
            ))}
          </div>
        </section>

        <section className="dash-detail" aria-hidden="true">
          <div className="dash-detail-body">
            <SkeletonText lines={2} label="Loading transcript…" />
            <div style={{ marginTop: "1.25rem", display: "grid", gap: "0.6rem" }}>
              {Array.from({ length: 5 }, (_, index) => (
                <SkeletonBlock key={index} height={54} radius={10} />
              ))}
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="dash-split fade-in">
      <section className="trace-index" aria-label="Conversation index">
        <p className="trace-index-head">
          <span className="dash-detail-cluster-label">Conversations</span>
          <span className="trace-index-count">{conversations.length}</span>
        </p>

        {conversations.length === 0 ? (
          <p className="cluster-empty">No conversations found in this batch.</p>
        ) : (
          <ul className="trace-list">
            {conversations.map((conversation) => {
              const isActive = conversation.conversation_id === activeId;
              const worstSeverity = Math.max(...conversation.clusters.map((c) => c.severity));

              return (
                <li key={conversation.conversation_id}>
                  <button
                    type="button"
                    className={`trace-item${isActive ? " is-active" : ""}`}
                    aria-pressed={isActive}
                    onClick={() => setPickedId(conversation.conversation_id)}
                  >
                    <span className="trace-item-top">
                      <span className="trace-item-id">{conversation.conversation_id}</span>
                      <span className={`severity-pill severity-${worstSeverity}`}>
                        {SEVERITY_LABEL[worstSeverity] || worstSeverity}
                      </span>
                    </span>
                    <span className="trace-item-desc">{conversation.description}</span>
                    <span className="trace-item-clusters">
                      {conversation.clusters.map((c) => c.label).join(" · ")}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="dash-detail" aria-label="Conversation transcript">
        <div className="dash-detail-head">
          {active && (
            <p className="dash-detail-cluster">
              <span className="dash-detail-cluster-label">Transcript</span>
              <span className="dash-detail-cluster-name">{active.conversation_id}</span>
            </p>
          )}
        </div>

        <div className="dash-detail-body">
          {active ? (
            <EvidencePanel
              key={active.conversation_id}
              evidence={{
                label: `Detected as: ${active.clusters.map((c) => c.label).join(" · ")}`,
                instances: [active],
              }}
            />
          ) : (
            <div className="page-state">Select a conversation to read its transcript.</div>
          )}
        </div>
      </section>
    </div>
  );
}
