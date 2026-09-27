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
  priority: (batch = "before") => get(`/api/priority?batch=${batch}`),
  clusterEvidence: (clusterId, batch = "before") =>
    get(`/api/clusters/${clusterId}/evidence?batch=${batch}`),
  clusterRootCause: (clusterId, batch = "before") =>
    get(`/api/clusters/${clusterId}/root-cause?batch=${batch}`),
  clusterFixComparison: (clusterId, batch = "before") =>
    get(`/api/clusters/${clusterId}/fix-comparison?batch=${batch}`),
  conversation: (conversationId, batch = "before") =>
    get(`/api/conversations/${conversationId}?batch=${batch}`),
  failures: (batch = "before") => get(`/api/failures?batch=${batch}`),
  fixComparison: () => get("/api/fix-comparison"),
};
