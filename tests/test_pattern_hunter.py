import unittest

from ai.pattern_hunter import find_patterns


class PatternHunterTests(unittest.TestCase):
    def setUp(self):
        self.findings = [{
            "conversation_id": "conv-1",
            "workflow": "inventory_check",
            "failure_type": "sample_failure",
            "description": "Repeated inventory lookup made no progress.",
            "evidence_turn_ids": [2, 3, 4],
        }]

    def test_same_local_cluster_id_is_scoped_by_batch(self):
        before = find_patterns(self.findings, batch_id="before")
        after = find_patterns(self.findings, batch_id="after")

        self.assertEqual(before[0]["cluster_id"], after[0]["cluster_id"])
        self.assertEqual(before[0]["batch_id"], "before")
        self.assertEqual(after[0]["batch_id"], "after")
        self.assertNotEqual(
            (before[0]["batch_id"], before[0]["cluster_id"]),
            (after[0]["batch_id"], after[0]["cluster_id"]),
        )
        self.assertEqual(before[0]["instances"][0]["evidence_turn_ids"], [2, 3, 4])

    def test_empty_findings_return_no_clusters(self):
        self.assertEqual(find_patterns([], batch_id="before"), [])

    def test_batch_id_must_be_a_non_empty_string(self):
        for batch_id in (None, "", "   ", 1):
            with self.subTest(batch_id=batch_id):
                with self.assertRaises(ValueError):
                    find_patterns(self.findings, batch_id=batch_id)


if __name__ == "__main__":
    unittest.main()