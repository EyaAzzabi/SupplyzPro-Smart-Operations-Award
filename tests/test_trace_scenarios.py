import json
import unittest
from pathlib import Path

from ai.failure_detective import detect_failures
from ai.trace_investigator import TraceFormatError, normalize_trace

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(filename):
    return json.loads((FIXTURES / filename).read_text(encoding="utf-8"))


class TraceScenarioTests(unittest.TestCase):
    def test_normal_trace_normalizes_and_is_not_flagged(self):
        conversation = normalize_trace(load_fixture("normal_trace.json"))

        self.assertEqual(conversation["conversation_id"], "mock_normal_001")
        self.assertEqual(detect_failures(conversation), [])

    def test_failure_trace_is_detected_with_evidence_turn(self):
        conversation = normalize_trace(load_fixture("failure_trace.json"))

        findings = detect_failures(conversation)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["failure_type"], "silent_tool_failure")
        self.assertEqual(findings[0]["evidence_turn_ids"], [2])

    def test_malformed_trace_is_rejected_before_detection(self):
        with self.assertRaisesRegex(TraceFormatError, "unique and increasing"):
            normalize_trace(load_fixture("malformed_trace.json"))


if __name__ == "__main__":
    unittest.main()