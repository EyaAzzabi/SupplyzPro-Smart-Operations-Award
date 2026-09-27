"""
Generates synthetic SupplyzPro agent-conversation logs with deliberately
seeded "hidden" failures: cases where a tool call technically returns a
response, but the agent's next message to the user is wrong, misleading,
or hides a problem.

Produces two batches:
  - conversations_before.json : the retry-loop duplicate-order bug is present
  - conversations_after.json  : the same bug, but patched with an idempotency
                                 check, used to demonstrate the fix worked

Run: python data/generate_conversations.py
"""

import json
import random
from pathlib import Path

SKUS = [f"SKU-{n}" for n in range(1000, 1030)]
SUPPLIERS = {
    "SUP-010": "Northline Parts",
    "SUP-011": "Kasserine Metal Co",
    "SUP-012": "Atlas Freight",
    "SUP-013": "Delta Components",
    "SUP-014": "Meridian Supply",
}
WAREHOUSES = ["WH-1", "WH-2", "WH-3"]

OUT_DIR = Path(__file__).parent


def _order_id(rng):
    return f"PO-{rng.randint(10000, 99999)}"


def gen_normal(rng, conv_id, workflow):
    """A conversation with no hidden failure -- used as noise."""
    sku = rng.choice(SKUS)
    qty = rng.choice([50, 100, 150, 200])
    supplier_id = rng.choice(list(SUPPLIERS))
    supplier_name = SUPPLIERS[supplier_id]

    if workflow == "inventory_check":
        stock = rng.randint(10, 500)
        turns = [
            {"turn_id": 1, "role": "user", "text": f"How many units of {sku} do we have in stock?"},
            {
                "turn_id": 2, "role": "agent",
                "text": f"You currently have {stock} units of {sku} in stock.",
                "tool_call": {
                    "tool_name": "check_inventory",
                    "parameters": {"sku": sku},
                    "response": {"sku": sku, "quantity": stock, "warehouse": rng.choice(WAREHOUSES)},
                    "latency_ms": rng.randint(80, 300),
                    "error_code": None,
                },
            },
        ]
    elif workflow == "purchase_order":
        order_id = _order_id(rng)
        turns = [
            {"turn_id": 1, "role": "user", "text": f"Order {qty} units of {sku} from {supplier_name}."},
            {
                "turn_id": 2, "role": "agent",
                "text": f"Order placed for {qty} units of {sku}. Order ID: {order_id}.",
                "tool_call": {
                    "tool_name": "create_purchase_order",
                    "parameters": {"sku": sku, "quantity": qty, "supplier_id": supplier_id},
                    "response": {"order_id": order_id, "status": "confirmed"},
                    "latency_ms": rng.randint(150, 400),
                    "error_code": None,
                    "idempotency_key": f"idem-{conv_id}",
                },
            },
        ]
    elif workflow == "supplier_lookup":
        lead_time = rng.randint(3, 21)
        turns = [
            {"turn_id": 1, "role": "user", "text": f"What's the lead time for {supplier_name}?"},
            {
                "turn_id": 2, "role": "agent",
                "text": f"{supplier_name}'s current lead time is {lead_time} days.",
                "tool_call": {
                    "tool_name": "get_supplier_info",
                    "parameters": {"supplier_id": supplier_id},
                    "response": {"supplier_id": supplier_id, "name": supplier_name, "lead_time_days": lead_time},
                    "latency_ms": rng.randint(80, 250),
                    "error_code": None,
                },
            },
        ]
    else:  # shipment_tracking
        order_id = _order_id(rng)
        eta = f"2026-09-{rng.randint(20, 29)}"
        turns = [
            {"turn_id": 1, "role": "user", "text": f"What's the ETA for order {order_id}?"},
            {
                "turn_id": 2, "role": "agent",
                "text": f"Order {order_id} is expected to arrive on {eta}.",
                "tool_call": {
                    "tool_name": "get_shipment_status",
                    "parameters": {"order_id": order_id},
                    "response": {"order_id": order_id, "eta": eta, "status": "in_transit"},
                    "latency_ms": rng.randint(80, 250),
                    "error_code": None,
                },
            },
        ]

    return {
        "conversation_id": conv_id,
        "workflow": workflow,
        "failure_type": None,
        "turns": turns,
    }


def gen_retry_loop_duplicate_order(rng, conv_id, fixed=False):
    """Tool call times out client-side but actually succeeded server-side;
    the agent retries without checking prior state, creating a duplicate
    order. When `fixed`, an idempotency key lets the retry return the
    original order instead of creating a new one."""
    sku = rng.choice(SKUS)
    qty = rng.choice([100, 150, 200, 250])
    supplier_id = rng.choice(list(SUPPLIERS))
    supplier_name = SUPPLIERS[supplier_id]
    idem_key = f"idem-{conv_id}"
    first_order = _order_id(rng)

    turns = [
        {"turn_id": 1, "role": "user", "text": f"Order {qty} units of {sku} from {supplier_name}."},
        {
            "turn_id": 2, "role": "agent",
            "text": "One moment, placing the order now.",
            "tool_call": {
                "tool_name": "create_purchase_order",
                "parameters": {"sku": sku, "quantity": qty, "supplier_id": supplier_id},
                "response": {"order_id": first_order, "status": "confirmed"},
                "latency_ms": 9000,
                "error_code": "client_timeout",
                "idempotency_key": idem_key,
            },
        },
    ]

    if fixed:
        second_order = first_order  # deduped by idempotency key
        note = f"Order placed for {qty} units of {sku}. Order ID: {first_order}."
    else:
        second_order = _order_id(rng)
        note = f"Order placed for {qty} units of {sku}. Order ID: {second_order}."

    turns.append({
        "turn_id": 3, "role": "agent",
        "text": "That timed out, retrying.",
        "tool_call": {
            "tool_name": "create_purchase_order",
            "parameters": {"sku": sku, "quantity": qty, "supplier_id": supplier_id},
            "response": {"order_id": second_order, "status": "confirmed"},
            "latency_ms": 300,
            "error_code": None,
            "idempotency_key": idem_key,
        },
    })
    turns.append({"turn_id": 4, "role": "agent", "text": note})

    return {
        "conversation_id": conv_id,
        "workflow": "purchase_order",
        "failure_type": None if fixed else "retry_loop_duplicate_order",
        "turns": turns,
    }


def gen_silent_tool_failure(rng, conv_id):
    """Tool returns success:false but the agent tells the user it's done."""
    order_id = _order_id(rng)
    bad_date = "2026-13-40"
    turns = [
        {"turn_id": 1, "role": "user", "text": f"Update the ETA for order {order_id} to next Tuesday."},
        {
            "turn_id": 2, "role": "agent",
            "text": "Done! I've updated the ETA.",
            "tool_call": {
                "tool_name": "update_shipment_eta",
                "parameters": {"order_id": order_id, "eta": bad_date},
                "response": {"success": False, "reason": "invalid_date_format"},
                "latency_ms": rng.randint(80, 200),
                "error_code": None,
            },
        },
    ]
    return {
        "conversation_id": conv_id,
        "workflow": "shipment_tracking",
        "failure_type": "silent_tool_failure",
        "turns": turns,
    }


def gen_hallucinated_tool_result(rng, conv_id):
    """Agent's claim doesn't match what the tool actually returned."""
    sku = rng.choice(SKUS)
    fabricated_qty = rng.choice([25, 40, 50, 75])
    turns = [
        {"turn_id": 1, "role": "user", "text": f"How many units of {sku} do we have in stock?"},
        {
            "turn_id": 2, "role": "agent",
            "text": f"You currently have {fabricated_qty} units of {sku} in stock.",
            "tool_call": {
                "tool_name": "check_inventory",
                "parameters": {"sku": sku},
                "response": {"sku": sku, "quantity": 0, "warehouse": rng.choice(WAREHOUSES)},
                "latency_ms": rng.randint(80, 250),
                "error_code": None,
            },
        },
    ]
    return {
        "conversation_id": conv_id,
        "workflow": "inventory_check",
        "failure_type": "hallucinated_tool_result",
        "turns": turns,
    }


def gen_wrong_tool_or_target(rng, conv_id):
    """Right intent, wrong record: looked up a different supplier than asked."""
    requested_id, requested_name = "SUP-011", SUPPLIERS["SUP-011"]
    wrong_id, wrong_name = "SUP-014", SUPPLIERS["SUP-014"]
    lead_time = rng.randint(3, 21)
    turns = [
        {"turn_id": 1, "role": "user", "text": f"What's the lead time for {requested_name}?"},
        {
            "turn_id": 2, "role": "agent",
            "text": f"{requested_name}'s current lead time is {lead_time} days.",
            "tool_call": {
                "tool_name": "get_supplier_info",
                "parameters": {"supplier_id": wrong_id},
                "response": {"supplier_id": wrong_id, "name": wrong_name, "lead_time_days": lead_time},
                "latency_ms": rng.randint(80, 250),
                "error_code": None,
            },
        },
    ]
    return {
        "conversation_id": conv_id,
        "workflow": "supplier_lookup",
        "failure_type": "wrong_tool_or_target",
        "turns": turns,
    }


def gen_context_collapse(rng, conv_id):
    """An earlier constraint (target warehouse) is dropped by a later tool call."""
    sku = rng.choice(SKUS)
    qty = rng.choice([300, 400, 500])
    stated_warehouse = "WH-2"
    actual_warehouse = "WH-1"
    order_id = _order_id(rng)
    supplier_id = rng.choice(list(SUPPLIERS))

    turns = [
        {"turn_id": 1, "role": "user", "text": f"Order {qty} units of {sku}, ship to {stated_warehouse} only."},
        {"turn_id": 2, "role": "agent", "text": f"Got it, {qty} units of {sku} to {stated_warehouse}."},
        {"turn_id": 3, "role": "user", "text": "Also add a note for fragile handling."},
        {
            "turn_id": 4, "role": "agent",
            "text": f"Order placed for {qty} units of {sku} with a fragile-handling note.",
            "tool_call": {
                "tool_name": "create_purchase_order",
                "parameters": {
                    "sku": sku, "quantity": qty, "supplier_id": supplier_id,
                    "warehouse": actual_warehouse, "note": "fragile handling",
                    "stated_warehouse": stated_warehouse,
                },
                "response": {"order_id": order_id, "status": "confirmed"},
                "latency_ms": rng.randint(150, 400),
                "error_code": None,
            },
        },
    ]
    return {
        "conversation_id": conv_id,
        "workflow": "purchase_order",
        "failure_type": "context_collapse",
        "turns": turns,
    }


def gen_user_frustration(rng, conv_id):
    """User has to rephrase the same request multiple times -- a signal that
    never shows up as a system error but indicates something is wrong."""
    sku = rng.choice(SKUS)
    turns = [
        {"turn_id": 1, "role": "user", "text": f"What is the stock level for {sku}?"},
        {"turn_id": 2, "role": "agent", "text": "I can help with orders and shipments -- could you clarify?"},
        {"turn_id": 3, "role": "user", "text": f"I'm asking how much stock we have of {sku}."},
        {"turn_id": 4, "role": "agent", "text": "Sorry, could you rephrase your question?"},
        {"turn_id": 5, "role": "user", "text": f"How many units of {sku} are in stock right now?"},
        {
            "turn_id": 6, "role": "agent",
            "text": f"You have units of {sku} in stock.",
            "tool_call": {
                "tool_name": "check_inventory",
                "parameters": {"sku": sku},
                "response": {"sku": sku, "quantity": rng.randint(10, 200), "warehouse": rng.choice(WAREHOUSES)},
                "latency_ms": rng.randint(80, 200),
                "error_code": None,
            },
        },
    ]
    return {
        "conversation_id": conv_id,
        "workflow": "inventory_check",
        "failure_type": "user_frustration_signal",
        "turns": turns,
    }


def build_batch(seed, n_conversations, retry_loop_bug_present, retry_loop_count, other_failure_count):
    rng = random.Random(seed)
    workflows = ["inventory_check", "purchase_order", "supplier_lookup", "shipment_tracking"]
    conversations = []
    idx = 0

    def next_id():
        nonlocal idx
        idx += 1
        return f"conv_{idx:04d}"

    for _ in range(retry_loop_count):
        conversations.append(
            gen_retry_loop_duplicate_order(rng, next_id(), fixed=not retry_loop_bug_present)
        )

    generators = [gen_silent_tool_failure, gen_hallucinated_tool_result,
                  gen_wrong_tool_or_target, gen_context_collapse, gen_user_frustration]
    for i in range(other_failure_count):
        conversations.append(generators[i % len(generators)](rng, next_id()))

    remaining = n_conversations - len(conversations)
    for _ in range(remaining):
        conversations.append(gen_normal(rng, next_id(), rng.choice(workflows)))

    rng.shuffle(conversations)
    return conversations


def main():
    before = build_batch(
        seed=42, n_conversations=60,
        retry_loop_bug_present=True, retry_loop_count=10, other_failure_count=15,
    )
    after = build_batch(
        seed=43, n_conversations=60,
        retry_loop_bug_present=False, retry_loop_count=10, other_failure_count=15,
    )

    (OUT_DIR / "conversations_before.json").write_text(json.dumps(before, indent=2))
    (OUT_DIR / "conversations_after.json").write_text(json.dumps(after, indent=2))
    print(f"Wrote {len(before)} conversations to conversations_before.json")
    print(f"Wrote {len(after)} conversations to conversations_after.json")


if __name__ == "__main__":
    main()
