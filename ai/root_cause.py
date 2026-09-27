"""Root-cause analysis: moves beyond "what happened" (the cluster label)
to "why it happened" -- a causal chain from the observed event down to a
preventive control.

Deterministic and template-based per failure type, not LLM-generated:
we constructed the taxonomy ourselves, so the causal chain for each type
is a known fact, not something that needs inference. Confidence labels
follow the "don't claim certainty you don't have" principle -- most of
these are "strongly_supported" (directly implied by the evidence pattern)
rather than "observed" (literally present in a single data field).
"""

CAUSAL_CHAINS = {
    "retry_loop_duplicate_order": {
        "causal_chain": [
            {"stage": "observed_event", "description": "create_purchase_order timed out on the client side."},
            {"stage": "immediate_failure", "description": "The agent retried the identical request without checking whether the first attempt had already succeeded server-side."},
            {"stage": "contributing_factor", "description": "The retry carried no idempotency key, so the backend had no way to recognize it as a duplicate of the first attempt."},
            {"stage": "likely_root_cause", "description": "Missing idempotency protection on the order-creation tool integration."},
            {"stage": "preventive_control", "description": "Attach a stable idempotency key per user intent; have the backend deduplicate on it and return the original order on a repeat."},
        ],
        "root_cause": "Missing idempotency protection on the order-creation tool integration",
        "confidence": "strongly_supported",
        "contributing_factors": ["No idempotency key on retry", "No check of prior tool-call outcome before retrying"],
    },
    "silent_tool_failure": {
        "causal_chain": [
            {"stage": "observed_event", "description": "A tool call returned an explicit error or a success:false payload."},
            {"stage": "immediate_failure", "description": "The agent's next message to the user did not surface the error in any form."},
            {"stage": "contributing_factor", "description": "No validation step checks a tool's response status before the agent narrates an outcome to the user."},
            {"stage": "likely_root_cause", "description": "Missing tool-result verification between the tool call and the agent's response generation."},
            {"stage": "preventive_control", "description": "Require an explicit success/failure check on every tool response before the agent is allowed to claim an outcome."},
        ],
        "root_cause": "Missing tool-result verification before the agent narrates an outcome",
        "confidence": "strongly_supported",
        "contributing_factors": ["No response-status check", "No guardrail blocking a success claim after an error"],
    },
    "hallucinated_tool_result": {
        "causal_chain": [
            {"stage": "observed_event", "description": "The tool returned a specific value (e.g. a quantity or status)."},
            {"stage": "immediate_failure", "description": "The agent's stated claim to the user does not match that value."},
            {"stage": "contributing_factor", "description": "The agent's response is generated without grounding-checking it against the tool's actual payload."},
            {"stage": "likely_root_cause", "description": "No verification step compares the agent's claim to the tool's raw response before the message is sent."},
            {"stage": "preventive_control", "description": "Add a post-generation check that every stated fact traces back to a specific field in a tool response."},
        ],
        "root_cause": "No grounding check between the agent's claim and the tool's raw response",
        "confidence": "strongly_supported",
        "contributing_factors": ["No fact-grounding step", "No penalty/flag for unsupported claims"],
    },
    "wrong_tool_or_target": {
        "causal_chain": [
            {"stage": "observed_event", "description": "The user named a specific entity (e.g. a supplier)."},
            {"stage": "immediate_failure", "description": "The tool was called against a different entity's ID than the one requested."},
            {"stage": "contributing_factor", "description": "Entity resolution (matching a name to the correct ID) is not verified before the tool call is issued."},
            {"stage": "likely_root_cause", "description": "Weak or missing entity-resolution/disambiguation step ahead of tool invocation."},
            {"stage": "preventive_control", "description": "Confirm the resolved entity's name back to the user (or check it against the request) before calling the tool."},
        ],
        "root_cause": "Weak entity resolution ahead of tool invocation",
        "confidence": "likely",
        "contributing_factors": ["No confirmation of resolved entity before tool call", "Similar entity names/IDs not disambiguated"],
    },
    "context_collapse": {
        "causal_chain": [
            {"stage": "observed_event", "description": "The user stated a constraint earlier in the conversation (e.g. a target warehouse)."},
            {"stage": "immediate_failure", "description": "A later tool call used a different value for that same field, with no acknowledgment of the change."},
            {"stage": "contributing_factor", "description": "Earlier-conversation constraints are not carried forward into later tool-call parameter construction."},
            {"stage": "likely_root_cause", "description": "Missing or weak conversation-state management across turns."},
            {"stage": "preventive_control", "description": "Maintain an explicit running state of user-specified constraints and diff tool-call parameters against it before calling."},
        ],
        "root_cause": "Missing or weak conversation-state management across turns",
        "confidence": "likely",
        "contributing_factors": ["No persistent constraint tracking", "No diff/confirmation when a tracked value changes"],
    },
    "no_progress_search_loop": {
        "causal_chain": [
            {"stage": "observed_event", "description": "The agent called the same read-only tool with identical parameters multiple times."},
            {"stage": "immediate_failure", "description": "No new information was gained between calls, and no answer was ever surfaced to the user."},
            {"stage": "contributing_factor", "description": "The agent has no mechanism to recognize it already has the answer it keeps re-fetching."},
            {"stage": "likely_root_cause", "description": "Missing repeated-call detection / no working-memory check before issuing a tool call."},
            {"stage": "preventive_control", "description": "Cache tool results within a conversation and check for an identical prior call before issuing a new one."},
        ],
        "root_cause": "Missing repeated-call detection before issuing a tool call",
        "confidence": "strongly_supported",
        "contributing_factors": ["No within-conversation result cache", "No loop/stall detection"],
    },
    "user_frustration_signal": {
        "causal_chain": [
            {"stage": "observed_event", "description": "The user rephrased or pushed back on the same request across multiple turns."},
            {"stage": "immediate_failure", "description": "The agent's responses did not resolve the request on the first or second attempt."},
            {"stage": "contributing_factor", "description": "The agent may be misunderstanding intent, or requiring information the user has already provided."},
            {"stage": "likely_root_cause", "description": "Possible intent-understanding gap or redundant clarification requests -- cannot be fully confirmed from conversational text alone."},
            {"stage": "preventive_control", "description": "Log repeated-rephrasing patterns for human review; consider escalation after N unresolved attempts."},
        ],
        "root_cause": "Possible intent-understanding gap or redundant clarification (not fully confirmable from text alone)",
        "confidence": "possible",
        "contributing_factors": ["Repeated user rephrasing", "No escalation path after repeated attempts"],
    },
}


def analyze_root_cause(failure_type):
    """Returns the causal-chain analysis for a failure type, or an honest
    'unknown' result for a type outside our taxonomy rather than guessing."""
    template = CAUSAL_CHAINS.get(failure_type)
    if template is None:
        return {
            "root_cause": "Not available -- failure type outside the known taxonomy.",
            "confidence": "unknown",
            "causal_chain": [],
            "contributing_factors": [],
        }
    return template
