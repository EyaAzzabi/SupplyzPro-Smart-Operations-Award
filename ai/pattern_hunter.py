"""Assign batch-scoped identity to clusters produced by the clustering layer."""

from ai.cluster import cluster_instances


def find_patterns(instances, batch_id, k=None):
    """Cluster findings with the existing algorithm and tag each cluster's batch.

    Cluster IDs are local to a clustering run. Callers must use the composite
    identity ``(batch_id, cluster_id)`` and must not compare IDs across batches.
    """
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id must be a non-empty string")

    clusters = cluster_instances(instances, k=k)
    for cluster in clusters:
        cluster["batch_id"] = batch_id
    return clusters