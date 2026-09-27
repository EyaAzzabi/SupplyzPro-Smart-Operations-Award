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

## Member 2 graph handoff

Run `python -m ai.run_pipeline` to generate `results/agent_1_3_output.json`. This deterministic, versioned artifact is the integration input for Member 2's graph; the existing separate result files remain available to the API and database seeder.

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

## Member 2 analysis handoff

The mock Agent 4-6 artifact is `results/agent_4_6_output.json`. It is a
versioned handoff consumed by the database loader and backend; it does not
change the Agent 1-3 artifact. Every analysis record uses the same composite
cluster identity as the producer artifact: `(batch_id, cluster_id)`.

```json
{
  "artifact_type": "xray.agent_4_6_output",
  "schema_version": 1,
  "consumer_of": "xray.agent_1_3_output",
  "producer_stages": ["root_cause_analyst", "priority_strategist", "fix_replay"],
  "root_causes": [
    {
      "batch_id": "before",
      "cluster_id": 1,
      "failure_type": "retry_loop_duplicate_order",
      "explanation": "Human-readable root-cause explanation.",
      "contributing_factors": ["factor one", "factor two"]
    }
  ],
  "priority_scores": [
    {
      "batch_id": "before",
      "cluster_id": 1,
      "frequency": 10,
      "severity": 3,
      "blast_radius": 1,
      "score": 30,
      "rank": 1
    }
  ],
  "fix_replays": [
    {
      "batch_id": "before",
      "cluster_id": 1,
      "failure_type": "retry_loop_duplicate_order",
      "replay_mode": "aggregate",
      "frequency_before_fix": 10,
      "frequency_after_fix": 0,
      "pass_rate": 1.0,
      "probes": [
        {"conversation_id": "probe_retry_loop_duplicate_order_00", "caught": true}
      ]
    }
  ]
}
```

`root_causes` and `priority_scores` contain one record per analyzed cluster.
`fix_replays` contains one record per replay comparison and may contain a
`probes` list. Version 1 uses `replay_mode: "aggregate"`: replay output is
represented by before/after frequency deltas, detector pass rate, and probe
outcomes rather than storing full replay transcripts. A future full replay
artifact can add a `conversations` list without changing the cluster key.

The priority fields are repeated intentionally at this handoff boundary so
the analysis result is self-contained and auditable. The loader must verify
that each referenced `(batch_id, cluster_id)` exists in Agent 1-3 output
before inserting it into analysis tables.

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

The cluster-scoped fix-comparison route reads `fix_replays`. Older databases
that only contain `regression_probes` are supported as a temporary fallback.

## Validation

Install the dependencies from `requirements.txt`, then run the route and temporary-database loader tests:

```bash
python -m unittest tests.test_backend_api -v
```