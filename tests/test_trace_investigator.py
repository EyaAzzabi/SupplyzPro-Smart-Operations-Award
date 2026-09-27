import unittest
import json
from pathlib import Path

from ai.trace_investigator import TraceFormatError, normalize_trace, normalize_traces


class TraceInvestigatorTests(unittest.TestCase):
    def test_project_conversation_sets_normalize_to_the_same_canonical_shape(self):
        data_dir = Path(__file__).parent.parent / "data"
        for filename in ("conversations_before.json", "conversations_after.json"):
            with self.subTest(filename=filename):
                conversations = json.loads((data_dir / filename).read_text())
                normalized = normalize_traces(conversations)
                self.assertEqual(len(normalized), len(conversations))
                self.assertEqual(normalized[0]["conversation_id"], conversations[0]["conversation_id"])
                self.assertEqual(normalized[0]["turns"][0]["turn_id"], 1)

    def test_canonical_conversation_is_normalized_without_mutating_input(self):
        trace = {
            "conversation_id": "conv-1",
            "workflow": "inventory_check",
            "failure_type": None,
            "turns": [
                {"turn_id": 1, "role": "user", "text": "Check stock."},
                {
                    "turn_id": 2,
                    "role": "assistant",
                    "text": "Checking.",
                    "tool_call": {
                        "tool_name": "check_inventory",
                        "parameters": {"sku": "SKU-1000"},
                        "response": {"quantity": 12},
                        "latency_ms": 80,
                        "error_code": None,
                    },
                },
            ],
        }

        normalized = normalize_trace(trace)

        self.assertEqual(normalized["turns"][1]["role"], "agent")
        self.assertEqual(normalized["turns"][1]["tool_call"]["response"], {"quantity": 12})
        self.assertEqual(trace["turns"][1]["role"], "assistant")
        self.assertEqual(normalize_trace(normalized), normalized)

    def test_chat_messages_link_tool_results_and_preserve_reward(self):
        trace = {
            "id": "trace-2",
            "reward": 0.0,
            "messages": [
                {"role": "system", "content": "Ignored instruction."},
                {"role": "user", "content": "Find my order."},
                {
                    "role": "assistant",
                    "content": "Looking it up.",
                    "tool_calls": [{
                        "id": "call-1",
                        "function": {
                            "name": "lookup_order",
                            "arguments": "{\"order_id\": \"A-1\"}",
                        },
                    }],
                },
                {"role": "tool", "tool_call_id": "call-1", "content": "{\"status\": \"shipped\"}"},
                {"role": "assistant", "content": "It shipped."},
            ],
        }

        normalized = normalize_trace(trace, default_workflow="retail")

        self.assertEqual(normalized["conversation_id"], "trace-2")
        self.assertEqual(normalized["workflow"], "retail")
        self.assertEqual(normalized["task_reward"], 0.0)
        self.assertEqual(len(normalized["turns"]), 3)
        tool_turn = normalized["turns"][1]
        self.assertEqual(tool_turn["tool_call"]["parameters"], {"order_id": "A-1"})
        self.assertEqual(tool_turn["tool_call"]["response"], {"status": "shipped"})

    def test_tau_trajectory_uses_default_workflow_and_keeps_bad_arguments(self):
        trace = {
            "conversation_id": "tau-1",
            "traj": [
                {"role": "user", "content": "Search."},
                {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": "call-1",
                        "function": {"name": "search", "arguments": "not-json"},
                    }],
                },
                {"role": "tool", "tool_call_id": "call-1", "content": "Error: unavailable"},
            ],
        }

        normalized = normalize_trace(trace)

        self.assertEqual(normalized["workflow"], "retail_customer_service")
        call = normalized["turns"][1]["tool_call"]
        self.assertEqual(call["parameters"], {"raw_arguments": "not-json"})
        self.assertEqual(call["response"], {"text": "Error: unavailable"})
        self.assertEqual(call["error_code"], "tool_error")

    def test_rejects_unmatched_tool_response(self):
        with self.assertRaises(TraceFormatError):
            normalize_trace({
                "conversation_id": "trace-3",
                "messages": [{"role": "tool", "tool_call_id": "missing", "content": "{}"}],
            })

    def test_rejects_duplicate_turn_ids(self):
        with self.assertRaises(TraceFormatError):
            normalize_trace({
                "conversation_id": "trace-4",
                "workflow": "test",
                "turns": [
                    {"turn_id": 1, "role": "user", "text": "First."},
                    {"turn_id": 1, "role": "agent", "text": "Second."},
                ],
            })

    def test_normalize_traces_requires_a_list(self):
        with self.assertRaises(TraceFormatError):
            normalize_traces({"conversation_id": "trace-5"})


if __name__ == "__main__":
    unittest.main()