import { useState } from "react";
import ClusterAnalysis from "../ClusterAnalysis";
import ClusterTable from "../ClusterTable";
import EvidencePanel from "../EvidencePanel";
import { SkeletonBlock, SkeletonCard, SkeletonTable, SkeletonText } from "../SkeletonLoader";
import Tabs from "../Tabs";
import { useClusterDetail, useOverview } from "../../hooks/useXrayData";
import "../Dashboard.css";

const TABS = [
  { id: "evidence", label: "Evidence", icon: "search" },
  { id: "root-cause", label: "Root Cause", icon: "brain" },
  { id: "remediation", label: "Remediation", icon: "tool" },
];

const FULL_TABLE_COLUMNS = ["24px", "30%", "26%", "18%", "56px", "48px"];

export default function FailureClustersPage({ selectedId, onSelect }) {
  const { clusters, loading, error } = useOverview();
  const [activeTab, setActiveTab] = useState("evidence");

  const activeId = selectedId ?? clusters[0]?.cluster_id ?? null;
  const selectedCluster = clusters.find((cluster) => cluster.cluster_id === activeId) ?? null;

  const {
    evidence,
    evidenceLoading,
    evidenceError,
    analysis,
    analysisLoading,
    analysisError,
  } = useClusterDetail(activeId);

  if (error) {
    return <p className="error">Couldn't reach the API: {error}. Is the backend running?</p>;
  }

  if (loading) {
    return (
      <div className="dash-split fade-in" role="status" aria-busy="true">
        <span className="sr-only">Loading clusters…</span>
        <section className="dash-clusters">
          <SkeletonBlock height={20} radius={6} />
          <div style={{ marginTop: "1rem" }}>
            <SkeletonTable rows={6} columnWidths={FULL_TABLE_COLUMNS} label="Loading clusters…" />
          </div>
        </section>

        <section className="dash-detail" aria-hidden="true">
          <div className="dash-detail-body">
            <SkeletonText lines={2} label="Loading cluster analysis…" />
            <div style={{ marginTop: "1.25rem", display: "grid", gap: "0.75rem" }}>
              <SkeletonCard height={92} label="Loading cluster analysis…" />
              <SkeletonCard height={92} label="Loading cluster analysis…" />
              <SkeletonCard height={92} label="Loading cluster analysis…" />
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="dash-split fade-in">
      <section className="dash-clusters">
        <h2>All failure clusters</h2>
        <ClusterTable clusters={clusters} selectedId={activeId} onSelect={onSelect} />
      </section>

      <section className="dash-detail" aria-label="Cluster analysis">
        <div className="dash-detail-head">
          {selectedCluster && (
            <p className="dash-detail-cluster">
              <span className="dash-detail-cluster-label">Selected cluster</span>
              <span className="dash-detail-cluster-name">{selectedCluster.label}</span>
            </p>
          )}
          <Tabs
            tabs={TABS}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            ariaLabel="Cluster analysis views"
          />
        </div>

        <div className="dash-detail-body">
          {activeTab === "evidence" && (
            <div
              key={activeTab}
              className="tab-panel fade-in"
              role="tabpanel"
              id="tabpanel-evidence"
              aria-labelledby="tab-evidence"
            >
              {evidenceLoading ? (
                <div role="status" aria-busy="true">
                  <span className="sr-only">Loading transcript evidence…</span>
                  <SkeletonText lines={2} label="Loading transcript evidence…" />
                  <div style={{ marginTop: "1.25rem", display: "grid", gap: "0.75rem" }}>
                    <SkeletonCard height={140} label="Loading transcript evidence…" />
                    <SkeletonCard height={140} label="Loading transcript evidence…" />
                  </div>
                </div>
              ) : (
                <EvidencePanel evidence={evidence} error={evidenceError} />
              )}
            </div>
          )}

          {activeTab === "root-cause" && (
            <div
              key={activeTab}
              className="tab-panel fade-in"
              role="tabpanel"
              id="tabpanel-root-cause"
              aria-labelledby="tab-root-cause"
            >
              {analysisLoading ? (
                <div role="status" aria-busy="true">
                  <span className="sr-only">Loading root cause analysis…</span>
                  <SkeletonText lines={3} label="Loading root cause analysis…" />
                  <div style={{ marginTop: "1.25rem", display: "grid", gap: "0.75rem" }}>
                    <SkeletonCard height={86} label="Loading root cause analysis…" />
                    <SkeletonCard height={86} label="Loading root cause analysis…" />
                    <SkeletonCard height={86} label="Loading root cause analysis…" />
                  </div>
                </div>
              ) : (
                <ClusterAnalysis section="root-cause" analysis={analysis} error={analysisError} />
              )}
            </div>
          )}

          {activeTab === "remediation" && (
            <div
              key={activeTab}
              className="tab-panel fade-in"
              role="tabpanel"
              id="tabpanel-remediation"
              aria-labelledby="tab-remediation"
            >
              {analysisLoading ? (
                <div role="status" aria-busy="true">
                  <span className="sr-only">Loading remediation plan…</span>
                  <SkeletonText lines={2} label="Loading remediation plan…" />
                  <div style={{ marginTop: "1.25rem", display: "grid", gap: "0.75rem" }}>
                    <SkeletonCard height={78} label="Loading remediation plan…" />
                    <SkeletonCard height={78} label="Loading remediation plan…" />
                    <SkeletonCard height={78} label="Loading remediation plan…" />
                  </div>
                </div>
              ) : (
                <ClusterAnalysis section="remediation" analysis={analysis} error={analysisError} />
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
