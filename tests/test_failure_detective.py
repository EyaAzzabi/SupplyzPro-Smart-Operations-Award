import unittest
from unittest.mock import patch

from ai.failure_detective import FailureFindingError, detect_failures


class FailureDetectiveTests(unittest.TestCase):
    def setUp(self):
        self.conversation = {
            "conversation_id": "conv-test",
            "workflow": "inventory_check",
            "turns": [
                {"turn_id": 1, "role": "user", "text": "Check stock."},
                {"turn_id": 2, "role": "agent", "text": "The quantity is 10."},
            ],
        }
        self.rule_finding = self._finding("rule:test", [2])
        self.judge_evidence = [1, 2]
        self.judge_finding = self._finding("judge:test", self.judge_evidence)
        self.behavioral_finding = self._finding("behavioral:test", [1, 2])

    def _finding(self, detector, evidence_turn_ids):
        return {
            "conversation_id": "conv-test",
            "workflow": "inventory_check",
            "detector": detector,
            "failure_type": "test_failure",
            "description": "A test finding.",
            "evidence_turn_ids": evidence_turn_ids,
        }

    @patch("ai.failure_detective.run_behavioral")
    @patch("ai.failure_detective.run_llm_judge")
    @patch("ai.failure_detective.run_rule_based")
    def test_combines_detectors_in_order_and_preserves_evidence_ids(
        self, rule_detector, judge_detector, behavioral_detector
    ):
        rule_detector.return_value = [self.rule_finding]
        judge_detector.return_value = [self.judge_finding]
        behavioral_detector.return_value = [self.behavioral_finding]

        findings = detect_failures(self.conversation)

        self.assertEqual(
            [finding["detector"] for finding in findings],
            ["rule:test", "judge:test", "behavioral:test"],
        )
        self.assertIs(findings[1]["evidence_turn_ids"], self.judge_evidence)
        self.assertEqual(findings[1]["evidence_turn_ids"], [1, 2])
        rule_detector.assert_called_once_with(self.conversation)
        judge_detector.assert_called_once_with(self.conversation)
        behavioral_detector.assert_called_once_with(self.conversation)

    @patch("ai.failure_detective.run_behavioral", return_value=[])
    @patch("ai.failure_detective.run_llm_judge", return_value=[])
    @patch("ai.failure_detective.run_rule_based")
    def test_rejects_findings_that_reference_unknown_turn_ids(
        self, rule_detector, _judge_detector, _behavioral_detector
    ):
        rule_detector.return_value = [self._finding("rule:test", [99])]

        with self.assertRaisesRegex(FailureFindingError, "unknown turn IDs"):
            detect_failures(self.conversation)

    @patch("ai.failure_detective.run_behavioral", return_value=[])
    @patch("ai.failure_detective.run_llm_judge", return_value=[])
    @patch("ai.failure_detective.run_rule_based")
    def test_rejects_findings_without_evidence(
        self, rule_detector, _judge_detector, _behavioral_detector
    ):
        rule_detector.return_value = [self._finding("rule:test", [])]

        with self.assertRaisesRegex(FailureFindingError, "evidence turn IDs"):
            detect_failures(self.conversation)


if __name__ == "__main__":
    unittest.main()