import "./ClusterTable.css";

const SEVERITY_LABEL = { 1: "Low", 2: "Medium", 3: "High" };

function scoreTier(score) {
  if (score > 70) return { tone: "critical", label: "Critical" };
  if (score >= 30) return { tone: "medium", label: "Medium" };
  return { tone: "low", label: "Low" };
}

function prettifyType(failureType) {
  return String(failureType ?? "")
    .split("_")
    .filter(Boolean)
    .map((word, i) => (i === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word))
    .join(" ");
}

export default function ClusterTable({ clusters, selectedId, onSelect, compact = false }) {
  if (!clusters || clusters.length === 0) {
    return <p className="cluster-empty">No failure clusters detected for this batch yet.</p>;
  }

  const maxFrequency = Math.max(...clusters.map((c) => c.frequency), 1);

  return (
    <div className={`cluster-list${compact ? " is-compact" : ""}`}>
      <div className="cluster-header-row" aria-hidden="true">
        <span>ID</span>
        <span>Failure Type</span>
        {!compact && <span>Root Cause</span>}
        <span className="is-numeric">Score</span>
        <span className="is-numeric">Occurrences</span>
      </div>

      <ul className="cluster-body">
        {clusters.map((cluster, index) => {
          const tier = scoreTier(cluster.priority_score);
          const isSelected = cluster.cluster_id === selectedId;

          return (
            <li key={cluster.cluster_id} className="cluster-item">
              <div
                className={`cluster-row${isSelected ? " is-selected" : ""}${compact ? " is-compact" : ""}`}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
                data-cluster-id={cluster.cluster_id}
                onClick={() => onSelect(cluster.cluster_id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(cluster.cluster_id);
                  }
                }}
              >
                <span className="cluster-cell cluster-cell-rank">#{index + 1}</span>

                <span className="cluster-cell cluster-cell-type">{cluster.label}</span>

                {!compact && (
                  <span className="cluster-cell cluster-cell-meta">
                    <span className={`severity-pill severity-${cluster.severity}`}>
                      {SEVERITY_LABEL[cluster.severity] || cluster.severity}
                    </span>
                    <span className="cluster-workflows">{cluster.workflows_touched.join(" · ")}</span>
                  </span>
                )}

                {!compact && (
                  <span className="cluster-cell cluster-cell-root">
                    <span className="cluster-root-tag">{prettifyType(cluster.failure_type)}</span>
                  </span>
                )}

                <span className="cluster-cell cluster-cell-score">
                  <span className={`priority-badge priority-${tier.tone}`}>
                    <span className="priority-value">{cluster.priority_score}</span>
                    <span className="priority-label">{tier.label}</span>
                  </span>
                </span>

                <span className="cluster-cell cluster-cell-freq">
                  <span className="cluster-freq-value">{cluster.frequency}</span>
                  <span className="cluster-freq-track" aria-hidden="true">
                    <span
                      className="cluster-freq-fill"
                      style={{ width: `${Math.max(6, (cluster.frequency / maxFrequency) * 100)}%` }}
                    />
                  </span>
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
