"""Layer 3: behavioral signals.

Catches failures with no error code and no factual contradiction to point
to -- just a pattern in how the conversation unfolded: an earlier
constraint getting dropped, or the user having to repeat themselves.
"""

import difflib


def detect_context_collapse(conversation):
    """A tool call's parameters silently override a constraint the user
    stated earlier in the conversation, and the agent's confirmation
    doesn't mention the change."""
    instances = []
    for turn in conversation["turns"]:
        if "tool_call" not in turn:
            continue
        params = turn["tool_call"]["parameters"]
        if "stated_warehouse" in params and params.get("warehouse") != params.get("stated_warehouse"):
            if params["stated_warehouse"] not in turn["text"] and params.get("warehouse", "") not in turn["text"]:
                pass  # agent's text mentions neither -- still a collapse, fall through
            instances.append({
                "conversation_id": conversation["conversation_id"],
                "workflow": conversation["workflow"],
                "detector": "behavioral:context_collapse",
                "failure_type": "context_collapse",
                "description": (
                    f"User asked for warehouse '{params['stated_warehouse']}' earlier in the "
                    f"conversation, but the tool call in turn {turn['turn_id']} used "
                    f"'{params.get('warehouse')}' instead, with no confirmation of the change."
                ),
                "evidence_turn_ids": [turn["turn_id"]],
            })
    return instances


def detect_user_frustration(conversation, similarity_threshold=0.55):
    """Consecutive-ish user turns that are near-duplicates of each other --
    the user rephrasing the same request because the agent didn't get it."""
    instances = []
    user_turns = [t for t in conversation["turns"] if t["role"] == "user"]
    for i in range(len(user_turns) - 1):
        a, b = user_turns[i]["text"], user_turns[i + 1]["text"]
        ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
        shared_words = set(a.lower().split()) & set(b.lower().split())
        if ratio > similarity_threshold or len(shared_words) >= 4:
            instances.append({
                "conversation_id": conversation["conversation_id"],
                "workflow": conversation["workflow"],
                "detector": "behavioral:user_frustration_signal",
                "failure_type": "user_frustration_signal",
                "description": (
                    f"User had to rephrase the same request across turns "
                    f"{user_turns[i]['turn_id']} and {user_turns[i + 1]['turn_id']} "
                    f"-- never logged anywhere as a system issue."
                ),
                "evidence_turn_ids": [user_turns[i]["turn_id"], user_turns[i + 1]["turn_id"]],
            })
    return instances


def run_behavioral(conversation):
    return detect_context_collapse(conversation) + detect_user_frustration(conversation)
