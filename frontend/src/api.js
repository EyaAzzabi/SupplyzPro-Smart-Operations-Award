const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${API_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`${path} -> ${res.status}`);
  }
  return res.json();
}

export const api = {
  summary: () => get("/api/summary"),
  clusters: (batch = "before") => get(`/api/clusters?batch=${batch}`),
  clusterEvidence: (clusterId, batch = "before") =>
    get(`/api/clusters/${clusterId}/evidence?batch=${batch}`),
  clusterAnalysis: (clusterId, batch = "before") =>
    get(`/api/clusters/${clusterId}/analysis?batch=${batch}`),
  fixComparison: () => get("/api/fix-comparison"),
};
