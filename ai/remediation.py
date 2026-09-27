"""Concrete engineering remediations per failure type, across the layers
where a fix could actually be applied (tool layer, agent/prompt layer,
data layer, observability layer). Template-based and tied to the same
taxonomy as ai/root_cause.py -- every recommendation maps to a specific
root cause, not a generic "add more testing" suggestion.
"""

REMEDIATIONS = {
    "retry_loop_duplicate_order": [
        {"layer": "tool", "recommendation": "Require an idempotency key on every order-creating tool call; dedupe on it server-side.", "priority": "high"},
        {"layer": "agent", "recommendation": "Before retrying a timed-out call, check whether the prior attempt actually succeeded rather than assuming it failed.", "priority": "high"},
        {"layer": "observability", "recommendation": "Alert on any two order-creation calls with identical parameters within a short time window.", "priority": "medium"},
    ],
    "silent_tool_failure": [
        {"layer": "tool", "recommendation": "Standardize tool responses to always include an explicit success/failure field; never rely on the absence of an error field.", "priority": "high"},
        {"layer": "agent", "recommendation": "Add a guardrail step that blocks a 'success' narration if the paired tool response indicates failure.", "priority": "high"},
        {"layer": "observability", "recommendation": "Log every case where a tool error is followed by a non-error agent message.", "priority": "medium"},
    ],
    "hallucinated_tool_result": [
        {"layer": "agent", "recommendation": "Add a post-generation grounding check comparing every stated fact to the actual tool response before sending.", "priority": "high"},
        {"layer": "prompt", "recommendation": "Instruct the agent explicitly to quote or reference the tool's returned value rather than paraphrasing from memory.", "priority": "medium"},
        {"layer": "observability", "recommendation": "Sample and audit agent claims against tool payloads on a recurring basis.", "priority": "low"},
    ],
    "wrong_tool_or_target": [
        {"layer": "agent", "recommendation": "Confirm the resolved entity (name/ID) back to the user before issuing the tool call.", "priority": "high"},
        {"layer": "tool", "recommendation": "Return a human-readable entity name alongside the ID in lookup responses, so mismatches are visible.", "priority": "medium"},
        {"layer": "data", "recommendation": "Add fuzzy-match warnings when a resolved entity's name is a close-but-not-exact match to the request.", "priority": "medium"},
    ],
    "context_collapse": [
        {"layer": "agent", "recommendation": "Maintain an explicit running record of user-stated constraints and diff tool-call parameters against it before calling.", "priority": "high"},
        {"layer": "prompt", "recommendation": "Require the agent to restate any changed constraint explicitly rather than silently applying a default.", "priority": "medium"},
        {"layer": "observability", "recommendation": "Flag tool calls whose parameters conflict with an earlier user-stated value in the same conversation.", "priority": "medium"},
    ],
    "no_progress_search_loop": [
        {"layer": "agent", "recommendation": "Cache tool results within a conversation; check for an identical prior call before issuing a new one.", "priority": "high"},
        {"layer": "observability", "recommendation": "Detect and alert on 3+ identical read-only tool calls within one conversation.", "priority": "medium"},
    ],
    "user_frustration_signal": [
        {"layer": "agent", "recommendation": "Escalate to a human or a clarifying-question fallback after two unresolved rephrasing attempts.", "priority": "medium"},
        {"layer": "observability", "recommendation": "Track rephrasing-frequency as a standing UX health metric, independent of task completion.", "priority": "low"},
    ],
}


def recommend_remediation(failure_type):
    return REMEDIATIONS.get(failure_type, [{
        "layer": "unknown", "recommendation": "Not available -- failure type outside the known taxonomy.", "priority": "unknown",
    }])
