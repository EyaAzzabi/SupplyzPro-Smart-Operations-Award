# Evaluation results

Computed against synthetic ground truth in `data/conversations_before.json` (60 conversations).

- **Failure detection precision/recall**: 1.00 / 1.00 (TP=28, FP=0, FN=0)
- **Cluster precision/recall**: 1.00 / 1.00 (pairwise)
- **Root-cause accuracy**: 1.00 (n=28)
- **Silent-failure recall**: 1.00 (n=3)
- **Analysis latency**: detection 0.0034s, clustering 0.2127s, prioritization 0.0s, total 0.2162s for 60 conversations
- **Cost per analysis**: local-only (offline heuristic judge, no API calls), 0 LLM calls, estimated cost 0.0
- **Agents 4-6 handoff**: mock_artifact, 7 root-cause records, 7 priority records, 1 replay records, 0 LLM calls, estimated cost 0.0
