"""Normalize raw agent traces into the conversation shape used by X-Ray."""

import json
from copy import deepcopy


class TraceFormatError(ValueError):
    """Raised when a trace cannot be converted without losing structure."""


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _arguments(value):
    if isinstance(value, dict):
        return deepcopy(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"raw_arguments": value}
        if isinstance(parsed, dict):
            return parsed
    return {"raw_arguments": _text(value)}


def _response(value):
    if not isinstance(value, str):
        return deepcopy(value)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {"text": value}


def _tool_call(tool_name, parameters, response=None, latency_ms=None, error_code=None, call=None):
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise TraceFormatError("tool calls must include a non-empty tool name")
    normalized = {
        "tool_name": tool_name,
        "parameters": _arguments(parameters),
        "response": _response(response),
        "latency_ms": latency_ms,
        "error_code": error_code,
    }
    if call and "idempotency_key" in call:
        normalized["idempotency_key"] = deepcopy(call["idempotency_key"])
    return normalized


def _canonical_turns(turns):
    if not isinstance(turns, list):
        raise TraceFormatError("turns must be a list")

    normalized = []
    seen_ids = set()
    previous_id = 0
    for index, turn in enumerate(turns, start=1):
        if not isinstance(turn, dict):
            raise TraceFormatError(f"turn {index} must be an object")
        turn_id = turn.get("turn_id", index)
        if isinstance(turn_id, bool) or not isinstance(turn_id, int) or turn_id < 1:
            raise TraceFormatError(f"turn {index} must have a positive integer turn_id")
        if turn_id in seen_ids or turn_id <= previous_id:
            raise TraceFormatError("turn_id values must be unique and increasing")
        seen_ids.add(turn_id)
        previous_id = turn_id

        role = turn.get("role")
        role = {"assistant": "agent", "human": "user"}.get(role, role)
        if role not in {"user", "agent"}:
            raise TraceFormatError(f"turn {turn_id} has unsupported role {role!r}")

        normalized_turn = {
            "turn_id": turn_id,
            "role": role,
            "text": _text(turn.get("text")),
        }
        if "tool_call" in turn:
            call = turn["tool_call"]
            if not isinstance(call, dict):
                raise TraceFormatError(f"turn {turn_id} tool_call must be an object")
            normalized_turn["tool_call"] = _tool_call(
                call.get("tool_name"),
                call.get("parameters", {}),
                call.get("response"),
                call.get("latency_ms"),
                call.get("error_code"),
                call,
            )
        normalized.append(normalized_turn)
    return normalized


def _trajectory_turns(messages):
    if not isinstance(messages, list):
        raise TraceFormatError("traj/messages must be a list")

    turns = []
    pending_calls = {}
    next_turn_id = 0

    def append_turn(role, text, tool_call=None):
        nonlocal next_turn_id
        next_turn_id += 1
        turn = {"turn_id": next_turn_id, "role": role, "text": _text(text)}
        if tool_call is not None:
            turn["tool_call"] = tool_call
        turns.append(turn)
        return turn

    for index, message in enumerate(messages, start=1):
        if not isinstance(message, dict):
            raise TraceFormatError(f"message {index} must be an object")
        role = message.get("role")
        if role in {"system", "developer"}:
            continue
        if role == "user":
            append_turn("user", message.get("content"))
            continue
        if role == "assistant":
            calls = message.get("tool_calls") or []
            if not isinstance(calls, list):
                raise TraceFormatError(f"message {index} tool_calls must be a list")
            if not calls:
                append_turn("agent", message.get("content"))
                continue
            for call in calls:
                if not isinstance(call, dict):
                    raise TraceFormatError("tool calls must be objects")
                call_id = call.get("id")
                function = call.get("function")
                if not isinstance(call_id, str) or not call_id:
                    raise TraceFormatError("raw tool calls must include an id")
                if call_id in pending_calls:
                    raise TraceFormatError(f"duplicate tool call id {call_id!r}")
                if not isinstance(function, dict):
                    raise TraceFormatError(f"tool call {call_id!r} must include a function object")
                normalized_call = _tool_call(
                    function.get("name"), function.get("arguments", {}), call=call
                )
                pending_calls[call_id] = append_turn(
                    "agent", message.get("content"), normalized_call
                )
            continue
        if role == "tool":
            call_id = message.get("tool_call_id")
            turn = pending_calls.get(call_id)
            if turn is None:
                raise TraceFormatError(f"tool response references unknown call id {call_id!r}")
            raw_response = message.get("content")
            turn["tool_call"]["response"] = _response(raw_response)
            if message.get("error_code") is not None:
                turn["tool_call"]["error_code"] = message["error_code"]
            elif isinstance(raw_response, str) and raw_response.lower().startswith("error"):
                turn["tool_call"]["error_code"] = "tool_error"
            continue
        raise TraceFormatError(f"message {index} has unsupported role {role!r}")

    return turns


def normalize_trace(trace, default_workflow=None, conversation_id=None):
    """Convert a canonical conversation or chat/tool-call trace to X-Ray format.

    Accepts the project's ``turns`` format and raw chat transcripts using
    either ``messages`` or Tau-Bench's ``traj`` key.
    """
    if not isinstance(trace, dict):
        raise TraceFormatError("trace must be an object")

    trace_id = (
        trace.get("conversation_id")
        or trace.get("trace_id")
        or trace.get("id")
        or conversation_id
    )
    if not isinstance(trace_id, (str, int)) or not str(trace_id).strip():
        raise TraceFormatError("trace must include a conversation_id, trace_id, or id")

    has_turns = "turns" in trace
    if has_turns:
        turns = _canonical_turns(trace["turns"])
    else:
        message_key = "traj" if "traj" in trace else "messages" if "messages" in trace else None
        if message_key is None:
            raise TraceFormatError("trace must include turns, messages, or traj")
        turns = _trajectory_turns(trace[message_key])

    workflow = trace.get("workflow") or default_workflow
    if not workflow and not has_turns and ("traj" in trace):
        workflow = "retail_customer_service"
    workflow = workflow or "unknown"
    if not isinstance(workflow, str):
        raise TraceFormatError("workflow must be a string")

    reserved = {
        "conversation_id", "trace_id", "id", "workflow", "turns", "messages",
        "traj", "reward", "task_reward", "failure_type",
    }
    normalized = {key: deepcopy(value) for key, value in trace.items() if key not in reserved}
    normalized.update({
        "conversation_id": str(trace_id),
        "workflow": workflow,
        "failure_type": trace.get("failure_type"),
        "turns": turns,
    })
    if "task_reward" in trace or "reward" in trace:
        normalized["task_reward"] = deepcopy(trace.get("task_reward", trace.get("reward")))
    return normalized


def normalize_traces(traces, default_workflow=None):
    """Normalize a batch of conversation records."""
    if not isinstance(traces, list):
        raise TraceFormatError("traces must be a list")
    return [normalize_trace(trace, default_workflow=default_workflow) for trace in traces]