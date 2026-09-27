import { useEffect, useState } from "react";
import { api } from "./api";
import ClusterTable from "./components/ClusterTable";
import EvidencePanel from "./components/EvidencePanel";
import FixComparison from "./components/FixComparison";
import "./App.css";

export default function App() {
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
    if (selectedId === null) return;
    setEvidenceLoading(true);
    setEvidenceError(null);
    api
      .clusterEvidence(selectedId)
      .then(setEvidence)
      .catch((err) => setEvidenceError(err.message))
      .finally(() => setEvidenceLoading(false));
  }, [selectedId]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔍 FailureLens</h1>
        <p className="tagline">
          We don't just find bugs in AI-agent conversations — we group them by root cause,
          rank them by real impact, and prove a fix works.
        </p>
      </header>

      {error && <p className="error">Couldn't reach the API: {error}. Is the backend running?</p>}

      {summary && (
        <div className="summary-banner">
          Analyzed <strong>{summary.total_conversations}</strong> synthetic SupplyzPro agent
          conversations and found <strong>{summary.total_failures}</strong> hidden failures across{" "}
          <strong>{summary.cluster_count}</strong> root-cause clusters.
        </div>
      )}

      <section>
        <h2>Failure clusters, ranked by Priority Score = Frequency × Severity × Blast Radius</h2>
        <ClusterTable clusters={clusters} selectedId={selectedId} onSelect={setSelectedId} />
      </section>

      <section>
        <h2>Evidence</h2>
        <EvidencePanel evidence={evidence} loading={evidenceLoading} error={evidenceError} />
      </section>

      <section>
        <FixComparison data={fixData} />
      </section>

      <footer className="disclosure">
        <strong>Disclosure:</strong> all conversation data shown is synthetic, generated to
        represent plausible SupplyzPro workflows with deliberately seeded failure patterns. AI
        tools used: an LLM-as-judge (NVIDIA NIM-hosted model, or an offline heuristic fallback)
        for hallucination/wrong-target detection, and TF-IDF/KMeans for root-cause clustering.
      </footer>
    </div>
  );
}
