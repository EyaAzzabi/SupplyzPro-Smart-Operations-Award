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
      "batch_id": "before",
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

## Versioned pipeline artifact

Run `python -m ai.run_pipeline` to generate `results/agent_1_3_output.json` alongside the existing `results_before.json`/`results_after.json`. It's the same clusters and evidence, bundled with a `schema_version` and `producer_stages` list so a future consumer can validate what produced it instead of assuming the shape never changes -- the database seeder still reads the separate result files directly, not this artifact.

```json
{
  "artifact_type": "xray.agent_1_3_output",
  "schema_version": 1,
  "producer_stages": ["trace_investigator", "failure_detective", "pattern_hunter"],
  "batches": {
    "before": {
      "batch_id": "before",
      "total_conversations": 60,
      "clusters": [],
      "conversations_by_id": {}
    },
    "after": {
      "batch_id": "after",
      "total_conversations": 60,
      "clusters": []
    }
  }
}
```

Clusters use the existing ranked cluster shape and include `batch_id`; findings and evidence turn IDs remain nested in each cluster's `instances`. The `before` batch includes full conversations for evidence lookup. The `after` batch intentionally contains cluster summaries only. Treat identity as `(batch_id, cluster_id)` and compare failure categories across batches by `failure_type`.

## Trace Investigator input

`ai.trace_investigator.normalize_trace` accepts either an already-canonical conversation with `turns`, or a raw chat trace with `messages` or Tau-Bench's `traj`. Raw chat roles `assistant` and `human` become `agent` and `user`; system/developer messages are omitted. Assistant tool calls and their tool replies are joined into one canonical agent turn by call ID. JSON arguments/responses are parsed; unparseable values are retained under `raw_arguments` or `text` rather than discarded. An unmatched tool reply or invalid turn structure raises `TraceFormatError` so ingestion can report the bad trace.

`normalize_traces` accepts a list of records. It is called by the pipeline before detection so downstream agents always receive the canonical conversation shape. A caller can supply `default_workflow` for raw records; Tau-Bench `traj` records default to `retail_customer_service`, and other missing workflows become `unknown`.

## Failure Detective output

`ai.failure_detective.detect_failures` runs the rule-based, LLM-judge, and behavioral layers in that order. It returns each detector finding unchanged, using the failure-instance shape (`conversation_id`, `workflow`, `detector`, `failure_type`, `description`, `evidence_turn_ids`). Before returning, it checks that every finding has the required fields and that its evidence turn IDs exist in the input conversation. It never reorders, renumbers, or replaces those IDs.

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

## Analysis tables (root cause, priority, fix replay)

Unlike Agent 1-3's output, root cause and priority are not a separate JSON
artifact -- `database/seed_db.py` computes them directly from
`ai/root_cause.py` and each cluster's own frequency/severity/blast_radius
while seeding, and writes them straight into two tables:

- `priority_scores(cluster_id, batch_id, frequency, severity, blast_radius, score, rank)`
- `root_causes(cluster_id, batch_id, failure_type, explanation, confidence, contributing_factors, causal_chain)`

Both are scoped `(cluster_id, batch_id)` and **only populated for the
`before` batch**. This is deliberate: `after`'s clusters come from a fresh
clustering run over a different conversation set, so an `after` cluster ID
is not the same issue as a `before` cluster ID with the same number (see
Cluster identity above) -- attaching root-cause text to it would silently
describe the wrong thing. `GET /api/clusters/{id}/root-cause?batch=after`
returns 404 for exactly this reason, not because seeding is incomplete.

Fix-replay data is not a separate table either -- it reuses
`regression_probes`, now scoped by `(cluster_id, batch_id)` instead of being
a single unscoped row. `ai/run_pipeline.py` tags the generated probes with
the top cluster's `cluster_id` before writing `results/regression_probes.json`,
and `seed_db.py` carries that through unchanged.

Root-cause explanations and remediation come from the same taxonomy-based
logic the dashboards already use (`ai/root_cause.py`, `ai/impact.py`,
`ai/remediation.py`) -- deterministic and keyed by `failure_type`, not
LLM-generated, since the causal chain for each of the 7 known failure types
is a fact we already know from having constructed the taxonomy ourselves.

## API shapes

`GET /api/priority?batch=before` returns the Agent 5 ranked list. Results are
ordered by `rank` and include the batch-scoped cluster identity, score inputs,
the calculated score, and cluster display metadata:

```json
[
  {
    "cluster_id": 1,
    "batch_id": "before",
    "label": "Retry-loop duplicate orders (no idempotency check)",
    "failure_type": "retry_loop_duplicate_order",
    "frequency": 10,
    "severity": 3,
    "blast_radius": 1,
    "score": 30,
    "rank": 1,
    "workflows_touched": ["purchase_order"]
  }
]
```

An existing batch with no priority rows returns an empty array. If the
database has not been reseeded with the analysis schema, the endpoint returns
HTTP 503 with a reseeding instruction.

`GET /api/clusters/{cluster_id}/root-cause?batch=before` returns the Agent 4
explanation for one batch-scoped cluster:

```json
{
  "cluster_id": 1,
  "batch_id": "before",
  "label": "Retry-loop duplicate orders (no idempotency check)",
  "failure_type": "retry_loop_duplicate_order",
  "explanation": "Human-readable root-cause explanation.",
  "contributing_factors": ["factor one", "factor two"]
}
```

Unknown clusters and clusters without a root-cause record return HTTP 404. If
the analysis table is missing because the database has not been reseeded, the
endpoint returns HTTP 503.

`GET /api/clusters?batch=before` returns an array of ranked cluster summaries. Each item includes `cluster_id`, `failure_type`, `label`, `frequency`, `severity`, `blast_radius`, `priority_score`, and `workflows_touched`.

`GET /api/conversations/{conversation_id}?batch=before` returns one canonical
conversation with its workflow, ground-truth failure type, and full transcript
including tool calls. Unknown conversations return HTTP 404.

`GET /api/failures?batch=before` returns a flat list of failure instances with
their cluster identity, detector, description, and evidence turn IDs. A batch
with no failures returns an empty array.

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

Both routes read `regression_probes`, scoped by `(cluster_id, batch_id)`.

## Validation

Install the dependencies from `requirements.txt`, then run the route and temporary-database loader tests:

```bash
python -m unittest tests.test_backend_api -v
```