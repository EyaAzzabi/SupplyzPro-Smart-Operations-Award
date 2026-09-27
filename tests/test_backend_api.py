import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from database.seed_db import seed_database

ROOT = Path(__file__).parent.parent


class BackendAPITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "test.db"
        seed_database(self.database_path, ROOT / "results")
        self.database_patch = patch("backend.main.DB_PATH", self.database_path)
        self.database_patch.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def test_priority_returns_analysis_ranked_list(self):
        response = self.client.get("/api/priority?batch=before")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 7)
        self.assertEqual(data[0]["cluster_id"], 1)
        self.assertEqual(data[0]["score"], 30)
        self.assertEqual(data[0]["rank"], 1)

    def test_root_cause_returns_batch_scoped_analysis(self):
        response = self.client.get("/api/clusters/1/root-cause?batch=before")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["batch_id"], "before")
        self.assertEqual(data["failure_type"], "retry_loop_duplicate_order")
        self.assertIn("client timeout hides server success", data["contributing_factors"])

    def test_root_cause_returns_404_for_missing_analysis_record(self):
        response = self.client.get("/api/clusters/1/root-cause?batch=after")

        self.assertEqual(response.status_code, 404)

    def test_fix_comparison_reads_analysis_replay(self):
        response = self.client.get("/api/clusters/1/fix-comparison?batch=before")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["top_cluster_label"], "Retry-loop duplicate orders (no idempotency check)")
        self.assertEqual(data["frequency_before_fix"], 10)
        self.assertEqual(len(data["probes"]), 5)

    def test_conversation_endpoint_returns_full_transcript(self):
        response = self.client.get("/api/conversations/conv_0002?batch=before")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["conversation_id"], "conv_0002")
        self.assertGreater(len(data["turns"]), 0)

    def test_failures_endpoint_returns_flat_instances(self):
        response = self.client.get("/api/failures?batch=before")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 28)
        self.assertIn("evidence_turn_ids", data[0])

    def test_cluster_fix_comparison_returns_only_requested_baseline_cluster(self):
        response = self.client.get("/api/clusters/1/fix-comparison?batch=before")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["cluster_id"], 1)
        self.assertEqual(data["batch_id"], "before")
        self.assertEqual(data["top_failure_type"], "retry_loop_duplicate_order")
        self.assertEqual(data["frequency_before_fix"], 10)
        self.assertEqual(data["frequency_after_fix"], 0)
        self.assertEqual(len(data["probes"]), 5)

    def test_cluster_fix_comparison_is_batch_scoped(self):
        response = self.client.get("/api/clusters/1/fix-comparison?batch=after")

        self.assertEqual(response.status_code, 404)

    def test_cluster_fix_comparison_returns_404_for_unknown_cluster(self):
        response = self.client.get("/api/clusters/999/fix-comparison")

        self.assertEqual(response.status_code, 404)

    def test_legacy_fix_comparison_still_returns_seeded_comparison(self):
        response = self.client.get("/api/fix-comparison")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cluster_id"], 1)

    def test_loader_populates_a_temporary_database_with_composite_probe_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results_dir = Path(temp_dir) / "results"
            results_dir.mkdir()
            database_path = Path(temp_dir) / "loader-test.db"
            cluster = {
                "cluster_id": 7,
                "failure_type": "sample_failure",
                "label": "Sample failure",
                "frequency": 1,
                "severity": 2,
                "blast_radius": 1,
                "priority_score": 2,
                "workflows_touched": ["sample"],
                "instances": [],
            }
            before = {
                "total_conversations": 0,
                "clusters": [cluster],
                "conversations_by_id": {},
            }
            after = {"total_conversations": 0, "clusters": [], "conversations_by_id": {}}
            probes = {
                "batch_id": "before",
                "cluster_id": 7,
                "top_failure_type": "sample_failure",
                "top_cluster_label": "Sample failure",
                "frequency_before_fix": 1,
                "frequency_after_fix": 0,
                "pass_rate": 1.0,
                "probes": [{"conversation_id": "sample_probe", "caught": True}],
            }
            (results_dir / "results_before.json").write_text(json.dumps(before))
            (results_dir / "results_after.json").write_text(json.dumps(after))
            (results_dir / "regression_probes.json").write_text(json.dumps(probes))

            seed_database(database_path, results_dir)

            conn = sqlite3.connect(database_path)
            try:
                row = conn.execute(
                    "SELECT cluster_id, batch_id, conversation_id, caught FROM regression_probes"
                ).fetchone()
            finally:
                conn.close()

        self.assertEqual(row, (7, "before", "sample_probe", 1))


if __name__ == "__main__":
    unittest.main()