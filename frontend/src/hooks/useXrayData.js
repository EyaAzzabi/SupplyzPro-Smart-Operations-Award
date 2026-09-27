import { useEffect, useState } from "react";
import { api } from "../api";

/** Summary + cluster list. Shared by the dashboard and the analysis pages. */
export function useOverview() {
  const [summary, setSummary] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.summary(), api.clusters()])
      .then(([summaryData, clusterData]) => {
        if (!active) return;
        setSummary(summaryData);
        setClusters(clusterData);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { summary, clusters, loading, error };
}

/** Transcripts + AI analysis for one selected cluster. */
export function useClusterDetail(clusterId) {
  const [evidenceState, setEvidenceState] = useState({ id: null, data: null, error: null });
  const [analysisState, setAnalysisState] = useState({ id: null, data: null, error: null });

  useEffect(() => {
    if (clusterId === null || clusterId === undefined) return undefined;

    let active = true;

    api
      .clusterEvidence(clusterId)
      .then((data) => {
        if (active) setEvidenceState({ id: clusterId, data, error: null });
      })
      .catch((err) => {
        if (active) setEvidenceState({ id: clusterId, data: null, error: err.message });
      });

    api
      .clusterAnalysis(clusterId)
      .then((data) => {
        if (active) setAnalysisState({ id: clusterId, data, error: null });
      })
      .catch((err) => {
        if (active) setAnalysisState({ id: clusterId, data: null, error: err.message });
      });

    return () => {
      active = false;
    };
  }, [clusterId]);

  const hasId = clusterId !== null && clusterId !== undefined;
  const evidenceSettled = hasId && evidenceState.id === clusterId;
  const analysisSettled = hasId && analysisState.id === clusterId;

  return {
    evidence: evidenceSettled ? evidenceState.data : null,
    evidenceLoading: hasId && !evidenceSettled,
    evidenceError: evidenceSettled ? evidenceState.error : null,
    analysis: analysisSettled ? analysisState.data : null,
    analysisLoading: hasId && !analysisSettled,
    analysisError: analysisSettled ? analysisState.error : null,
  };
}

/** Before/after fix frequencies + regression probe pass rate. */
export function useFixComparison() {
  const [fixData, setFixData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    api
      .fixComparison()
      .then((data) => {
        if (active) setFixData(data);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { fixData, loading, error };
}

/**
 * Flat conversation index built from every cluster's evidence, until the
 * backend exposes a dedicated /api/conversations endpoint. Deduplicated by
 * conversation id, keeping every cluster label a conversation belongs to.
 */
export function useConversationIndex(clusters) {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!clusters || clusters.length === 0) return undefined;

    let active = true;

    Promise.all(
      clusters.map((cluster) =>
        api
          .clusterEvidence(cluster.cluster_id)
          .then((data) => ({ cluster, data }))
          .catch(() => ({ cluster, data: null })),
      ),
    )
      .then((results) => {
        if (!active) return;

        const index = new Map();
        results.forEach(({ cluster, data }) => {
          (data?.instances ?? []).forEach((instance) => {
            const id = instance.conversation_id;
            if (!index.has(id)) {
              index.set(id, { ...instance, clusters: [] });
            }
            index.get(id).clusters.push({
              clusterId: cluster.cluster_id,
              label: cluster.label,
              severity: cluster.severity,
            });
          });
        });

        setConversations([...index.values()]);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [clusters]);

  const isEmpty = !clusters || clusters.length === 0;

  return { conversations, loading: !isEmpty && loading, error };
}
