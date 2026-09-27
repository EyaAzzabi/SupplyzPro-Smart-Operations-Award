"""Layer 2: LLM-as-judge.

Catches the failures that a rule can't see because the tool call
"succeeded" -- the agent's claim just doesn't match what the tool
actually returned, or it used the wrong record.

If NVIDIA_API_KEY is set, this calls NVIDIA's hosted NIM chat-completions
endpoint (OpenAI-compatible) with a rubric prompt and parses its verdict.
Without a key -- e.g. running this offline during development -- it falls
back to a deterministic heuristic that checks the same two things
(numbers match, named entity matches) so the rest of the pipeline is
testable without any external dependency. Swapping in a live NVIDIA NIM
call only requires setting NVIDIA_API_KEY in .env; no other code changes.
"""

import json
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

RUBRIC_PROMPT = """You are auditing an AI agent's tool use for a supply-chain \
operations product. You will be given the user's request, the exact \
parameters and raw response of a tool call, and the agent's next message \
to the user.

Answer strictly as JSON with these fields:
  hallucinated: true if the agent's message states a fact (a number, name, \
    status) that contradicts or is not supported by the tool's raw response.
  wrong_target: true if the tool was called against a different named \
    entity (e.g. a different supplier) than the one the user asked about.
  rationale: one sentence explaining your verdict.

User request: {user_text}
Tool: {tool_name}
Tool parameters: {parameters}
Tool raw response: {response}
Agent's message to the user: {agent_text}

JSON:"""


def _extract_json_object(content):
    """Reasoning models can emit chain-of-thought text before the answer,
    or nest an escaped duplicate of the JSON inside one of its own string
    values -- a regex either swallows too much (greedy) or breaks on
    nested braces (non-greedy, non-nested). Using the real JSON decoder's
    raw_decode at every '{' handles both correctly: it parses exactly one
    well-formed value from a given position, nested strings and all, so
    the first successful parse containing our expected keys is the actual
    outer answer object, not a fragment of it."""
    decoder = json.JSONDecoder()
    idx = 0
    while True:
        start = content.find("{", idx)
        if start == -1:
            return {"hallucinated": False, "wrong_target": False, "rationale": ""}
        try:
            obj, end = decoder.raw_decode(content, start)
            if isinstance(obj, dict) and ("hallucinated" in obj or "wrong_target" in obj):
                return obj
            idx = end
        except json.JSONDecodeError:
            idx = start + 1


def _call_nvidia_nim(user_text, tool_name, parameters, response, agent_text):
    api_key = os.environ.get("NVIDIA_API_KEY")
    base_url = os.environ.get("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.environ.get("NVIDIA_NIM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")

    prompt = RUBRIC_PROMPT.format(
        user_text=user_text, tool_name=tool_name, parameters=json.dumps(parameters),
        response=json.dumps(response), agent_text=agent_text,
    )
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 600,
            # Some NIM models spend the token budget on a hidden reasoning
            # pass before ever writing the visible answer, truncating it
            # (finish_reason="length") well before max_tokens looks like
            # it should be enough. Turning thinking off keeps the full
            # budget for the actual JSON answer.
            "chat_template_kwargs": {"thinking": False},
        },
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return _extract_json_object(content)


_CODE_TOKEN = re.compile(r"\b(?:SKU|PO|WH|SUP)-\d+\b", re.IGNORECASE)


def _numbers_in(text):
    """Numbers the agent actually stated as a claim (e.g. a quantity),
    excluding digits that are only part of an identifier like SKU-1010."""
    stripped = _CODE_TOKEN.sub("", text)
    return set(int(n) for n in re.findall(r"\d+", stripped))


def _fallback_judge(user_text, tool_name, parameters, response, agent_text):
    """Offline stand-in for the LLM judge: checks the same two things
    (claimed numbers match the tool response, claimed entity name matches
    the one the user asked about) with plain string/number comparison."""
    hallucinated = False
    if isinstance(response, dict) and "quantity" in response:
        claimed = _numbers_in(agent_text)
        actual = response["quantity"]
        if claimed and actual not in claimed:
            hallucinated = True

    wrong_target = False
    if isinstance(response, dict) and "name" in response:
        requested_name = None
        m = re.search(r"for ([A-Z][\w& ]+?)[\.\?]?$", user_text.strip())
        if m:
            requested_name = m.group(1).strip()
        if requested_name and requested_name.lower() not in response["name"].lower():
            wrong_target = True

    rationale = []
    if hallucinated:
        rationale.append("agent's stated quantity does not match the tool's raw response")
    if wrong_target:
        rationale.append("tool was called against a different named entity than the user requested")
    return {
        "hallucinated": hallucinated,
        "wrong_target": wrong_target,
        "rationale": "; ".join(rationale) or "no discrepancy found",
    }


def judge_tool_call(user_text, tool_name, parameters, response, agent_text):
    if os.environ.get("NVIDIA_API_KEY"):
        # Observed failures on this endpoint are transient (timeouts under
        # load), not deterministic errors -- successful calls consistently
        # return in 4-8s, failures hang to the timeout. One retry recovers
        # most of them instead of silently downgrading to the offline
        # heuristic on the first hiccup.
        for _attempt in range(2):
            try:
                return _call_nvidia_nim(user_text, tool_name, parameters, response, agent_text)
            except Exception:
                continue
    return _fallback_judge(user_text, tool_name, parameters, response, agent_text)


def _preceding_user_text(conversation, turn_id):
    prior = [t for t in conversation["turns"] if t["turn_id"] < turn_id and t["role"] == "user"]
    return prior[-1]["text"] if prior else ""


def run_llm_judge(conversation):
    instances = []
    for turn in conversation["turns"]:
        if "tool_call" not in turn:
            continue
        call = turn["tool_call"]
        user_text = _preceding_user_text(conversation, turn["turn_id"])
        verdict = judge_tool_call(
            user_text, call["tool_name"], call["parameters"], call.get("response"), turn["text"]
        )
        if verdict.get("hallucinated"):
            instances.append({
                "conversation_id": conversation["conversation_id"],
                "workflow": conversation["workflow"],
                "detector": "llm_judge:hallucinated_tool_result",
                "failure_type": "hallucinated_tool_result",
                "description": (
                    f"Agent's claim in turn {turn['turn_id']} does not match the raw response "
                    f"from '{call['tool_name']}'. {verdict.get('rationale', '')}"
                ),
                "evidence_turn_ids": [turn["turn_id"]],
            })
        if verdict.get("wrong_target"):
            instances.append({
                "conversation_id": conversation["conversation_id"],
                "workflow": conversation["workflow"],
                "detector": "llm_judge:wrong_tool_or_target",
                "failure_type": "wrong_tool_or_target",
                "description": (
                    f"'{call['tool_name']}' in turn {turn['turn_id']} was called against a different "
                    f"record than the one the user asked about. {verdict.get('rationale', '')}"
                ),
                "evidence_turn_ids": [turn["turn_id"]],
            })
    return instances
