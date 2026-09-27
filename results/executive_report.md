# X-Ray Executive Report

Analyzed **60** conversations and found **28** failures across **7** root-cause clusters.
Top priority: **Retry-loop duplicate orders (no idempotency check)**.

## Retry-loop duplicate orders (no idempotency check) (priority score 30)

**Root cause** (strongly supported by the evidence pattern): Missing idempotency protection on the order-creation tool integration

Causal chain:
- *observed event*: create_purchase_order timed out on the client side.
- *immediate failure*: The agent retried the identical request without checking whether the first attempt had already succeeded server-side.
- *contributing factor*: The retry carried no idempotency key, so the backend had no way to recognize it as a duplicate of the first attempt.
- *likely root cause*: Missing idempotency protection on the order-creation tool integration.
- *preventive control*: Attach a stable idempotency key per user intent; have the backend deduplicate on it and return the original order on a repeat.

**Observed impact:**
- 10 occurrence(s) detected in the analyzed conversations.
- Touches 1 distinct workflow(s): purchase_order.
**Potential impact:**
- Duplicate real-world purchase orders -- risk of double-shipping and inventory overcommitment.
- Unnecessary spend if the duplicate order is fulfilled before being caught.

**Recommended fixes:**
- [tool, high priority] Require an idempotency key on every order-creating tool call; dedupe on it server-side.
- [agent, high priority] Before retrying a timed-out call, check whether the prior attempt actually succeeded rather than assuming it failed.
- [observability, medium priority] Alert on any two order-creation calls with identical parameters within a short time window.

## Silent tool failures (error caught, never surfaced) (priority score 9)

**Root cause** (strongly supported by the evidence pattern): Missing tool-result verification before the agent narrates an outcome

Causal chain:
- *observed event*: A tool call returned an explicit error or a success:false payload.
- *immediate failure*: The agent's next message to the user did not surface the error in any form.
- *contributing factor*: No validation step checks a tool's response status before the agent narrates an outcome to the user.
- *likely root cause*: Missing tool-result verification between the tool call and the agent's response generation.
- *preventive control*: Require an explicit success/failure check on every tool response before the agent is allowed to claim an outcome.

**Observed impact:**
- 3 occurrence(s) detected in the analyzed conversations.
- Touches 1 distinct workflow(s): shipment_tracking.
**Potential impact:**
- Customer or downstream system receives false confirmation of an action that did not happen.
- Errors go untracked, so the same failure can recur silently and repeatedly.

**Recommended fixes:**
- [tool, high priority] Standardize tool responses to always include an explicit success/failure field; never rely on the absence of an error field.
- [agent, high priority] Add a guardrail step that blocks a 'success' narration if the paired tool response indicates failure.
- [observability, medium priority] Log every case where a tool error is followed by a non-error agent message.

## Hallucinated tool results (claim != actual data) (priority score 9)

**Root cause** (strongly supported by the evidence pattern): No grounding check between the agent's claim and the tool's raw response

Causal chain:
- *observed event*: The tool returned a specific value (e.g. a quantity or status).
- *immediate failure*: The agent's stated claim to the user does not match that value.
- *contributing factor*: The agent's response is generated without grounding-checking it against the tool's actual payload.
- *likely root cause*: No verification step compares the agent's claim to the tool's raw response before the message is sent.
- *preventive control*: Add a post-generation check that every stated fact traces back to a specific field in a tool response.

**Observed impact:**
- 3 occurrence(s) detected in the analyzed conversations.
- Touches 1 distinct workflow(s): inventory_check.
**Potential impact:**
- Business decisions (restocking, order confirmation) made on fabricated data.
- Erodes trust in the agent once a customer discovers the discrepancy.

**Recommended fixes:**
- [agent, high priority] Add a post-generation grounding check comparing every stated fact to the actual tool response before sending.
- [prompt, medium priority] Instruct the agent explicitly to quote or reference the tool's returned value rather than paraphrasing from memory.
- [observability, low priority] Sample and audit agent claims against tool payloads on a recurring basis.

## No-progress search loop (stuck re-querying, never resolved) (priority score 6)

**Root cause** (strongly supported by the evidence pattern): Missing repeated-call detection before issuing a tool call

Causal chain:
- *observed event*: The agent called the same read-only tool with identical parameters multiple times.
- *immediate failure*: No new information was gained between calls, and no answer was ever surfaced to the user.
- *contributing factor*: The agent has no mechanism to recognize it already has the answer it keeps re-fetching.
- *likely root cause*: Missing repeated-call detection / no working-memory check before issuing a tool call.
- *preventive control*: Cache tool results within a conversation and check for an identical prior call before issuing a new one.

**Observed impact:**
- 3 occurrence(s) detected in the analyzed conversations.
- Touches 1 distinct workflow(s): supplier_lookup.
**Potential impact:**
- Wasted tool-call cost and latency with no resolution for the user.
- User-facing delay that can itself become a frustration signal.

**Recommended fixes:**
- [agent, high priority] Cache tool results within a conversation; check for an identical prior call before issuing a new one.
- [observability, medium priority] Detect and alert on 3+ identical read-only tool calls within one conversation.

## Wrong tool/target selected (right intent, wrong record) (priority score 6)

**Root cause** (the likely explanation, though not certain): Weak entity resolution ahead of tool invocation

Causal chain:
- *observed event*: The user named a specific entity (e.g. a supplier).
- *immediate failure*: The tool was called against a different entity's ID than the one requested.
- *contributing factor*: Entity resolution (matching a name to the correct ID) is not verified before the tool call is issued.
- *likely root cause*: Weak or missing entity-resolution/disambiguation step ahead of tool invocation.
- *preventive control*: Confirm the resolved entity's name back to the user (or check it against the request) before calling the tool.

**Observed impact:**
- 3 occurrence(s) detected in the analyzed conversations.
- Touches 1 distinct workflow(s): supplier_lookup.
**Potential impact:**
- Information or actions applied to the wrong customer/supplier/order record.
- Potential data-privacy exposure if one party's data is surfaced to another.

**Recommended fixes:**
- [agent, high priority] Confirm the resolved entity (name/ID) back to the user before issuing the tool call.
- [tool, medium priority] Return a human-readable entity name alongside the ID in lookup responses, so mismatches are visible.
- [data, medium priority] Add fuzzy-match warnings when a resolved entity's name is a close-but-not-exact match to the request.

## Context collapse (earlier constraint silently dropped) (priority score 6)

**Root cause** (the likely explanation, though not certain): Missing or weak conversation-state management across turns

Causal chain:
- *observed event*: The user stated a constraint earlier in the conversation (e.g. a target warehouse).
- *immediate failure*: A later tool call used a different value for that same field, with no acknowledgment of the change.
- *contributing factor*: Earlier-conversation constraints are not carried forward into later tool-call parameter construction.
- *likely root cause*: Missing or weak conversation-state management across turns.
- *preventive control*: Maintain an explicit running state of user-specified constraints and diff tool-call parameters against it before calling.

**Observed impact:**
- 3 occurrence(s) detected in the analyzed conversations.
- Touches 1 distinct workflow(s): purchase_order.
**Potential impact:**
- Order fulfilled against terms the user did not actually agree to (e.g. wrong warehouse).
- Requires manual correction once discovered, adding operational overhead.

**Recommended fixes:**
- [agent, high priority] Maintain an explicit running record of user-stated constraints and diff tool-call parameters against it before calling.
- [prompt, medium priority] Require the agent to restate any changed constraint explicitly rather than silently applying a default.
- [observability, medium priority] Flag tool calls whose parameters conflict with an earlier user-stated value in the same conversation.

## User-frustration signal (repeated rephrasing) (priority score 3)

**Root cause** (a possible explanation, not confirmable from this data alone): Possible intent-understanding gap or redundant clarification (not fully confirmable from text alone)

Causal chain:
- *observed event*: The user rephrased or pushed back on the same request across multiple turns.
- *immediate failure*: The agent's responses did not resolve the request on the first or second attempt.
- *contributing factor*: The agent may be misunderstanding intent, or requiring information the user has already provided.
- *likely root cause*: Possible intent-understanding gap or redundant clarification requests -- cannot be fully confirmed from conversational text alone.
- *preventive control*: Log repeated-rephrasing patterns for human review; consider escalation after N unresolved attempts.

**Observed impact:**
- 3 occurrence(s) detected in the analyzed conversations.
- Touches 1 distinct workflow(s): inventory_check.
**Potential impact:**
- Degraded user experience even when the task eventually completes.
- Repeated unresolved friction may correlate with support escalations or churn.

**Recommended fixes:**
- [agent, medium priority] Escalate to a human or a clarifying-question fallback after two unresolved rephrasing attempts.
- [observability, low priority] Track rephrasing-frequency as a standing UX health metric, independent of task completion.
