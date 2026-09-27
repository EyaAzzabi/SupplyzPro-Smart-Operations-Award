"""Groups detected failure instances by root cause rather than by surface
symptom: instances are embedded (TF-IDF over their natural-language
description) and clustered, so a timeout in one workflow and a malformed
payload in another can still land in the same cluster if they share the
same underlying cause.
"""

from collections import Counter

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

CLUSTER_LABELS = {
    "retry_loop_duplicate_order": "Retry-loop duplicate orders (no idempotency check)",
    "silent_tool_failure": "Silent tool failures (error caught, never surfaced)",
    "hallucinated_tool_result": "Hallucinated tool results (claim != actual data)",
    "wrong_tool_or_target": "Wrong tool/target selected (right intent, wrong record)",
    "context_collapse": "Context collapse (earlier constraint silently dropped)",
    "user_frustration_signal": "User-frustration signal (repeated rephrasing)",
    "no_progress_search_loop": "No-progress search loop (stuck re-querying, never resolved)",
}


def cluster_instances(instances, k=None):
    """Returns a list of clusters: {label, failure_type, instances, ...}."""
    if not instances:
        return []

    descriptions = [i["description"] for i in instances]
    k = k or min(len(CLUSTER_LABELS), len(instances))

    if len(instances) == 1:
        labels = [0]
    else:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=200)
        X = vectorizer.fit_transform(descriptions)
        km = KMeans(n_clusters=min(k, X.shape[0]), random_state=0, n_init=10)
        labels = km.fit_predict(X)

    grouped = {}
    for instance, cluster_id in zip(instances, labels):
        grouped.setdefault(cluster_id, []).append(instance)

    clusters = []
    for cluster_id, members in grouped.items():
        dominant_type = Counter(m["failure_type"] for m in members).most_common(1)[0][0]
        clusters.append({
            "cluster_id": int(cluster_id),
            "failure_type": dominant_type,
            "label": CLUSTER_LABELS.get(dominant_type, dominant_type),
            "instances": members,
            "frequency": len(members),
            "workflows_touched": sorted(set(m["workflow"] for m in members)),
        })

    clusters.sort(key=lambda c: c["frequency"], reverse=True)
    return clusters
