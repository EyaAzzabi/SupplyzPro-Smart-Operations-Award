"""Layer 1: cheap, deterministic rule-based failure detection.

Catches the failures that leave an explicit trace: error codes, timeouts,
success:false payloads the agent didn't surface, and identical repeated
tool calls that indicate a retry loop.
"""


def _tool_turns(conversation):
    return [t for t in conversation["turns"] if "tool_call" in t]


def detect_silent_tool_failure(conversation):
    """A tool call errors out (explicit error_code, or an explicit
    success:false in the payload) but the agent's own message never
    surfaces that to the user."""
    instances = []
    for turn in _tool_turns(conversation):
        call = turn["tool_call"]
        if call["tool_name"] == "create_purchase_order":
            # A timed-out order call that gets retried is its own, more
            # specific failure category (see detect_retry_loop_duplicate_order)
            # rather than a generic silent failure.
            continue
        response = call.get("response") or {}
        errored = call.get("error_code") is not None or response.get("success") is False
        if not errored:
            continue
        agent_text = turn["text"].lower()
        surfaced = any(w in agent_text for w in ["sorry", "error", "couldn't", "failed", "unable", "issue"])
        if not surfaced:
            instances.append({
                "conversation_id": conversation["conversation_id"],
                "workflow": conversation["workflow"],
                "detector": "rule:silent_tool_failure",
                "failure_type": "silent_tool_failure",
                "description": (
                    f"Tool '{call['tool_name']}' returned an error/failure "
                    f"({call.get('error_code') or response.get('reason', 'unspecified')}) "
                    f"but the agent told the user it succeeded."
                ),
                "evidence_turn_ids": [turn["turn_id"]],
            })
    return instances


def detect_retry_loop_duplicate_order(conversation):
    """Two calls to the same order-creating tool with the same parameters
    that each return a *different* order_id -- a duplicate real-world
    action caused by retrying without checking prior state."""
    instances = []
    order_calls = [
        t for t in _tool_turns(conversation)
        if t["tool_call"]["tool_name"] == "create_purchase_order"
    ]
    for i in range(len(order_calls)):
        for j in range(i + 1, len(order_calls)):
            a, b = order_calls[i]["tool_call"], order_calls[j]["tool_call"]
            same_request = (
                a["parameters"].get("sku") == b["parameters"].get("sku")
                and a["parameters"].get("quantity") == b["parameters"].get("quantity")
                and a["parameters"].get("supplier_id") == b["parameters"].get("supplier_id")
            )
            if not same_request:
                continue
            order_a = (a.get("response") or {}).get("order_id")
            order_b = (b.get("response") or {}).get("order_id")
            if order_a and order_b and order_a != order_b:
                instances.append({
                    "conversation_id": conversation["conversation_id"],
                    "workflow": conversation["workflow"],
                    "detector": "rule:retry_loop_duplicate_order",
                    "failure_type": "retry_loop_duplicate_order",
                    "description": (
                        f"'create_purchase_order' was called twice for the same "
                        f"{a['parameters'].get('quantity')} units of {a['parameters'].get('sku')} "
                        f"after a timeout, producing two separate orders "
                        f"({order_a} and {order_b}) with no idempotency check."
                    ),
                    "evidence_turn_ids": [order_calls[i]["turn_id"], order_calls[j]["turn_id"]],
                })
    return instances


READ_ONLY_TOOLS = {"check_inventory", "get_supplier_info", "get_shipment_status"}


def detect_no_progress_search_loop(conversation, min_repeats=3):
    """The agent re-issues the exact same read-only query three or more
    times without ever resolving it -- distinct from a legitimate
    double-check (two identical calls is normal; three+ is a stuck loop)."""
    instances = []
    seen = {}
    for turn in _tool_turns(conversation):
        call = turn["tool_call"]
        if call["tool_name"] not in READ_ONLY_TOOLS:
            continue
        key = (call["tool_name"], tuple(sorted(call["parameters"].items())))
        seen.setdefault(key, []).append(turn["turn_id"])

    for (tool_name, params), turn_ids in seen.items():
        if len(turn_ids) >= min_repeats:
            instances.append({
                "conversation_id": conversation["conversation_id"],
                "workflow": conversation["workflow"],
                "detector": "rule:no_progress_search_loop",
                "failure_type": "no_progress_search_loop",
                "description": (
                    f"'{tool_name}' was called {len(turn_ids)} times with identical parameters "
                    f"({dict(params)}) without the agent ever surfacing an answer -- a stuck "
                    f"search loop making no progress."
                ),
                "evidence_turn_ids": turn_ids,
            })
    return instances


def run_rule_based(conversation):
    return (
        detect_silent_tool_failure(conversation)
        + detect_retry_loop_duplicate_order(conversation)
        + detect_no_progress_search_loop(conversation)
    )
