import { useEffect, useState } from "react";
import { api } from "../../api";
import ClusterTable from "../ClusterTable";
import EvidencePanel from "../EvidencePanel";
import FailureFamiliesChart from "../FailureFamiliesChart";
import FailureTrendChart from "../FailureTrendChart";
import FixComparison from "../FixComparison";
import StatsCards from "../StatsCards";

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [fixData, setFixData] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [error, setError] = useState(null);
  const [evidenceError, setEvidenceError] = useState(null);

  useEffect(() => {
    Promise.all([api.summary(), api.clusters(), api.fixComparison()])
      .then(([summaryData, clusterData, fixComparisonData]) => {
        setSummary(summaryData);
        setClusters(clusterData);
        setFixData(fixComparisonData);
        if (clusterData.length > 0) setSelectedId(clusterData[0].cluster_id);
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (selectedId === null) return undefined;
    let active = true;
    setEvidenceLoading(true);
    setEvidenceError(null);
    api
      .clusterEvidence(selectedId)
      .then((data) => {
        if (active) setEvidence(data);
      })
      .catch((err) => {
        if (active) setEvidenceError(err.message);
      })
      .finally(() => {
        if (active) setEvidenceLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  return (
    <>
      {error && <p className="error">Couldn't reach the API: {error}. Is the backend running?</p>}

      {summary && (
        <div className="summary-banner">
          Analyzed <strong>{summary.total_conversations}</strong> synthetic SupplyzPro agent
          conversations and found <strong>{summary.total_failures}</strong> hidden failures across{" "}
          <strong>{summary.cluster_count}</strong> root-cause clusters.
        </div>
      )}

      {summary && (
        <div className="stats-section">
          <StatsCards summary={summary} clusters={clusters} fixData={fixData} />
        </div>
      )}

      <section className="charts-section">
        <div className="charts-grid">
          <FailureTrendChart />
          <FailureFamiliesChart />
        </div>
      </section>

      <section>
        <h2>Failure clusters, ranked by Priority Score = Frequency × Severity × Blast Radius</h2>
        <ClusterTable clusters={clusters} selectedId={selectedId} onSelect={setSelectedId} />
      </section>

      <section>
        <h2>Evidence</h2>
        <EvidencePanel
          key={selectedId}
          evidence={evidence}
          loading={evidenceLoading}
          error={evidenceError}
        />
      </section>

      <section>
        <FixComparison data={fixData} />
      </section>

      <footer className="disclosure">
        <strong>Disclosure:</strong> all conversation data shown is synthetic, generated to represent
        plausible SupplyzPro workflows with deliberately seeded failure patterns. AI tools used: an
        LLM-as-judge (NVIDIA NIM-hosted model, or an offline heuristic fallback) for
        hallucination/wrong-target detection, and TF-IDF/KMeans for root-cause clustering.
      </footer>
    </>
  );
}
