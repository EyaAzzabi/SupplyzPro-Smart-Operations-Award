import FixComparison from "../FixComparison";
import { SkeletonBlock, SkeletonText } from "../SkeletonLoader";
import { useFixComparison } from "../../hooks/useXrayData";
import "../Dashboard.css";

export default function ReplayLabPage() {
  const { fixData, loading, error } = useFixComparison();

  if (error) {
    return <p className="error">Couldn't reach the API: {error}. Is the backend running?</p>;
  }

  if (loading) {
    return (
      <div className="dash-split fade-in" role="status" aria-busy="true">
        <span className="sr-only">Loading the replay lab…</span>
        <section className="dash-clusters" aria-hidden="true">
          <SkeletonBlock height={20} radius={6} />
          <div style={{ marginTop: "1rem", display: "grid", gap: "0.6rem" }}>
            <SkeletonText lines={4} label="Loading the replay lab…" />
          </div>
        </section>

        <section className="dash-detail" aria-hidden="true">
          <div className="dash-detail-body">
            <SkeletonBlock height={30} radius={6} />
            <div style={{ marginTop: "1.25rem", display: "grid", gap: "0.75rem" }}>
              <SkeletonBlock height={72} radius={10} />
              <SkeletonBlock height={72} radius={10} />
            </div>
            <div style={{ marginTop: "1.5rem", display: "grid", gap: "0.6rem" }}>
              {Array.from({ length: 4 }, (_, index) => (
                <SkeletonBlock key={index} height={44} radius={8} />
              ))}
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="dash-split fade-in">
      <section className="dash-clusters replay-intro">
        <h2>Before / after the fix</h2>
        <p className="dash-hint">
          The same failure pattern, counted across the analyzed batch before the mitigation was
          applied and after it was re-run. This is the proof that a proposed fix actually removes
          the failure instead of hiding it.
        </p>
        <p className="dash-hint">
          Pick a cluster in <strong>Failure Clusters</strong> to see its evidence, root cause and
          recommended remediations.
        </p>
      </section>

      <section className="dash-detail" aria-label="Replay lab">
        <div className="dash-detail-body">
          {fixData ? (
            <FixComparison data={fixData} />
          ) : (
            <div className="page-state">
              No before/after comparison available for this batch yet.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
