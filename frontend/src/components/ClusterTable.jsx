const SEVERITY_LABEL = { 1: "Low", 2: "Medium", 3: "High" };

export default function ClusterTable({ clusters, selectedId, onSelect }) {
  return (
    <table className="cluster-table">
      <thead>
        <tr>
          <th>Cluster</th>
          <th>Frequency</th>
          <th>Severity</th>
          <th>Blast radius</th>
          <th>Priority score</th>
          <th>Workflows</th>
        </tr>
      </thead>
      <tbody>
        {clusters.map((c) => (
          <tr
            key={c.cluster_id}
            className={c.cluster_id === selectedId ? "selected" : ""}
            onClick={() => onSelect(c.cluster_id)}
          >
            <td className="label-cell">{c.label}</td>
            <td>{c.frequency}</td>
            <td>
              <span className={`severity-pill severity-${c.severity}`}>
                {SEVERITY_LABEL[c.severity] || c.severity}
              </span>
            </td>
            <td>{c.blast_radius}</td>
            <td className="score-cell">{c.priority_score}</td>
            <td>{c.workflows_touched.join(", ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
