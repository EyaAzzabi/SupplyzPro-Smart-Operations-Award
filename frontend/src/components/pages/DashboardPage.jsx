import ClusterTable from "../ClusterTable";
import FailureFamiliesChart from "../FailureFamiliesChart";
import FailureTrendChart from "../FailureTrendChart";
import { SkeletonBlock, SkeletonCard, SkeletonTable } from "../SkeletonLoader";
import StatsCards from "../StatsCards";
import { useFixComparison, useOverview } from "../../hooks/useXrayData";
import "../Dashboard.css";

function DashboardSkeleton() {
  return (
    <div className="fade-in" aria-hidden="true">
      <div className="skeleton-cards">
        <div className="stats-grid">
          <SkeletonCard height={118} label="Loading metrics…" />
          <SkeletonCard height={118} label="Loading metrics…" />
          <SkeletonCard height={118} label="Loading metrics…" />
          <SkeletonCard height={118} label="Loading metrics…" />
        </div>
      </div>

      <section className="charts-section">
        <div className="charts-grid">
          <SkeletonBlock height={260} radius={12} />
          <SkeletonBlock height={260} radius={12} />
        </div>
      </section>

      <section className="dash-clusters-section">
        <SkeletonBlock height={20} radius={6} />
        <div style={{ marginTop: "1rem" }}>
          <SkeletonTable rows={6} label="Loading failure clusters…" />
        </div>
      </section>
    </div>
  );
}

export default function DashboardPage({ onSelectCluster }) {
  const { summary, clusters, loading, error } = useOverview();
  const { fixData } = useFixComparison();

  if (error) {
    return <p className="error">Couldn't reach the API: {error}. Is the backend running?</p>;
  }

  if (loading) {
    return (
      <div role="status" aria-busy="true">
        <span className="sr-only">Loading the overview…</span>
        <DashboardSkeleton />
      </div>
    );
  }

  return (
    <div className="fade-in">
      {summary && (
        <div className="stats-section">
          <StatsCards summary={summary} clusters={clusters} fixData={fixData} />
        </div>
      )}

      <section className="charts-section">
        <div className="charts-grid">
          <FailureTrendChart clusters={clusters} />
          <FailureFamiliesChart clusters={clusters} />
        </div>
      </section>

      <section className="dash-clusters-section">
        <h2>Failure clusters, ranked by Priority Score = Frequency × Severity × Blast Radius</h2>
        <ClusterTable clusters={clusters} compact onSelect={onSelectCluster} />
        <p className="dash-hint">
          Click any row to open the full analysis — evidence, root cause and remediation.
        </p>
      </section>
    </div>
  );
}
