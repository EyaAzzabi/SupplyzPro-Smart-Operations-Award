# Backend JSON Contract

This contract connects pipeline output, SQLite seeding, and the read-only API. The checked-in pipeline output is the source of truth for the examples.

## Cluster identity

`cluster_id` is an integer assigned by clustering and is only unique within one batch. Its database identity is `(batch_id, cluster_id)`. Do not assume that cluster ID `1` in `before` is the same issue as cluster ID `1` in `after`, or that an ID stays the same after re-running clustering. Use `failure_type` to compare a failure category between batches.

Regression probes are attached to the baseline cluster they test. Their `batch_id` is `before`; `cluster_id` refers to that batch. The fixed batch may no longer contain the failure cluster, so replay comparison must not require a matching cluster in `after`.

## Pipeline artifacts

`results_before.json` and `results_after.json` share this shape. Only the baseline artifact includes `conversations_by_id`, because evidence is displayed from the unfixed examples.

```json
{
  "total_conversations": 60,
  "clusters": [
    {
      "cluster_id": 1,
      "failure_type": "retry_loop_duplicate_order",
      "label": "Retry-loop duplicate orders (no idempotency check)",
      "frequency": 10,
      "severity": 3,
      "blast_radius": 1,
      "priority_score": 30,
      "workflows_touched": ["purchase_order"],
      "instances": [
        {
          "conversation_id": "conv_0002",
          "workflow": "purchase_order",
          "detector": "rule:retry_loop_duplicate_order",
          "failure_type": "retry_loop_duplicate_order",
          "description": "'create_purchase_order' was called twice for the same 150 units of SKU-1007 after a timeout, producing two separate orders (PO-98696 and PO-81482) with no idempotency check.",
          "evidence_turn_ids": [2, 3]
        }
      ]
    }
  ],
  "conversations_by_id": {
    "conv_0002": {
      "conversation_id": "conv_0002",
      "workflow": "purchase_order",
      "turns": [
        {"turn_id": 1, "role": "user", "text": "Place this order."},
        {
          "turn_id": 2,
          "role": "agent",
          "text": "Retrying the order.",
          "tool_call": {
            "tool_name": "create_purchase_order",
            "parameters": {"sku": "SKU-1007", "quantity": 150},
            "response": {"order_id": "PO-98696"},
            "latency_ms": 9000,
            "error_code": "timeout"
          }
        }
      ]
    }
  }
}
```

The example is abbreviated; real conversation turns and evidence are preserved in the generated files.

`results/regression_probes.json` identifies the tested baseline cluster explicitly:

```json
{
  "batch_id": "before",
  "cluster_id": 1,
  "top_failure_type": "retry_loop_duplicate_order",
  "top_cluster_label": "Retry-loop duplicate orders (no idempotency check)",
  "frequency_before_fix": 10,
  "frequency_after_fix": 0,
  "pass_rate": 1.0,
  "probes": [
    {"conversation_id": "probe_retry_loop_duplicate_order_00", "caught": true}
  ]
}
```

## API shapes

`GET /api/clusters?batch=before` returns an array of ranked cluster summaries. Each item includes `cluster_id`, `failure_type`, `label`, `frequency`, `severity`, `blast_radius`, `priority_score`, and `workflows_touched`.

`GET /api/clusters/{cluster_id}/evidence?batch=before` returns the cluster label and instances with their descriptions, `evidence_turn_ids`, and full transcript turns, including raw tool parameters and responses.

`GET /api/clusters/{cluster_id}/fix-comparison?batch=before` returns the replay comparison for that baseline cluster:

```json
{
  "cluster_id": 1,
  "batch_id": "before",
  "top_failure_type": "retry_loop_duplicate_order",
  "top_cluster_label": "Retry-loop duplicate orders (no idempotency check)",
  "frequency_before_fix": 10,
  "frequency_after_fix": 0,
  "pass_rate": 1.0,
  "probes": [
    {"conversation_id": "probe_retry_loop_duplicate_order_00", "caught": true}
  ]
}
```

The legacy `GET /api/fix-comparison` remains available for the existing dashboard and returns the first seeded comparison. New clients should use the cluster-scoped route. Unknown clusters and clusters without replay data return HTTP 404.

## Validation

Install the dependencies from `requirements.txt`, then run the route and temporary-database loader tests:

```bash
python -m unittest tests.test_backend_api -v
```