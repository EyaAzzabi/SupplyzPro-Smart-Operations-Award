import unittest

from ai.run_pipeline import build_agent_1_3_artifact


class AgentOutputArtifactTests(unittest.TestCase):
    def test_artifact_has_versioned_batches_and_baseline_evidence(self):
        before_cluster = {
            "batch_id": "before",
            "cluster_id": 1,
            "failure_type": "sample_failure",
            "instances": [{"conversation_id": "before-1", "evidence_turn_ids": [2]}],
        }
        after_cluster = {
            "batch_id": "after",
            "cluster_id": 1,
            "failure_type": "sample_failure",
            "instances": [{"conversation_id": "after-1", "evidence_turn_ids": [3]}],
        }
        before = [{
            "conversation_id": "before-1",
            "workflow": "inventory_check",
            "turns": [{"turn_id": 2, "role": "agent", "text": "Found stock."}],
        }]
        after = [{
            "conversation_id": "after-1",
            "workflow": "inventory_check",
            "turns": [{"turn_id": 3, "role": "agent", "text": "Found stock."}],
        }]

        artifact = build_agent_1_3_artifact(
            [before_cluster], [after_cluster], before, after
        )

        self.assertEqual(artifact["artifact_type"], "xray.agent_1_3_output")
        self.assertEqual(artifact["schema_version"], 1)
        self.assertEqual(
            artifact["producer_stages"],
            ["trace_investigator", "failure_detective", "pattern_hunter"],
        )
        before_batch = artifact["batches"]["before"]
        after_batch = artifact["batches"]["after"]
        self.assertEqual(before_batch["clusters"][0]["batch_id"], "before")
        self.assertEqual(after_batch["clusters"][0]["batch_id"], "after")
        self.assertEqual(
            (before_batch["clusters"][0]["batch_id"], before_batch["clusters"][0]["cluster_id"]),
            ("before", 1),
        )
        self.assertEqual(
            (after_batch["clusters"][0]["batch_id"], after_batch["clusters"][0]["cluster_id"]),
            ("after", 1),
        )
        self.assertEqual(
            before_batch["conversations_by_id"]["before-1"]["turns"][0]["turn_id"], 2
        )
        self.assertNotIn("conversations_by_id", after_batch)


if __name__ == "__main__":
    unittest.main()