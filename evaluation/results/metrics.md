# Evaluation results

Computed against synthetic ground truth in `data/conversations_before.json` (60 conversations).

- **Failure detection precision/recall**: 1.00 / 1.00 (TP=28, FP=0, FN=0)
- **Cluster precision/recall**: 1.00 / 1.00 (pairwise)
- **Root-cause accuracy**: 1.00 (n=28)
- **Silent-failure recall**: 1.00 (n=3)
- **Analysis latency**: detection 0.0022s, clustering 1.9286s, prioritization 0.0s, total 1.9308s for 60 conversations
- **Cost per analysis**: local-only (offline heuristic judge, no API calls), 0 LLM calls, estimated cost 0.0
