# database/

SQLite (`xray.db`), populated from the AI layer's output (`results/*.json`) — never written to directly by the backend.

## Schema

```
batches            one row per batch ('before' / 'after')
conversations      (conversation_id, batch_id) -> workflow, ground-truth failure_type
turns              one row per turn in a conversation (turn_number, role, text)
tool_calls         at most one per turn -- tool_name, parameters/response (JSON), latency, error_code
clusters           one row per root-cause cluster per batch -- label, frequency, severity, blast_radius, priority_score
failure_instances  one row per detected failure -- which cluster it landed in, which conversation/turns it's evidence for
regression_probes  one row per generated regression-test conversation for the top cluster, with caught (0/1)
root_causes         one Agent 4 explanation per batch-scoped cluster
priority_scores     one Agent 5 ranked score per batch-scoped cluster
fix_replays         one Agent 6 before/after comparison per tested cluster, with probe outcomes as JSON
```

`conversations` -> `turns` -> `tool_calls` is a normal 1-to-many chain, joined on `id`, not stringly-typed IDs. `clusters` -> `failure_instances` the same. Only `failure_instances.evidence_turn_ids` and `clusters.workflows_touched` stay as comma-separated text — they're small, fixed-shape lists read as a whole, not queried into or filtered on, so normalizing them into their own tables would add joins without adding any real capability.

Cluster IDs are scoped to a batch; use `(batch_id, cluster_id)` as the identity. Regression probes point to the baseline cluster with this composite key. See [`docs/backend-contract.md`](../docs/backend-contract.md) for JSON examples and API response shapes.

Only the "before" batch has its conversations/turns/tool_calls populated — the "after" batch (the simulated fix) only needs its cluster-level stats for the before/after comparison, there's no evidence to drill into for it.

Analysis records use the same `(batch_id, cluster_id)` identity as `clusters`.
The current Agent 4-6 mock handoff is `results/agent_4_6_output.json` and is
loaded automatically when present. Older result directories without that file
remain seedable.

## Regenerating

```bash
python -m ai.run_pipeline       # writes results/*.json from data/conversations_*.json
python -m database.seed_db      # drops and rebuilds xray.db from results/*.json
```

`seed_db.py` always drops and rebuilds the file from scratch — it's a derived artifact, never hand-edited.

## Example queries

```sql
-- top clusters for the 'before' batch
SELECT label, frequency, priority_score FROM clusters WHERE batch_id = 'before' ORDER BY priority_score DESC;

-- full transcript for one conversation
SELECT t.turn_number, t.role, t.text, tc.tool_name, tc.response_json
FROM turns t LEFT JOIN tool_calls tc ON tc.turn_id = t.id
WHERE t.conversation_id = 'conv_0001' AND t.batch_id = 'before'
ORDER BY t.turn_number;

-- every instance of a given failure type, with its evidence conversation
SELECT conversation_id, description FROM failure_instances WHERE failure_type = 'retry_loop_duplicate_order';
```
