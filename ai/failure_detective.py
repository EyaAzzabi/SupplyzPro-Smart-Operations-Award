"""Combines detector layers into validated, evidence-backed findings."""

from ai.behavioral import run_behavioral
from ai.llm_judge import run_llm_judge
from ai.rules import run_rule_based


class FailureFindingError(ValueError):
    """Raised when a detector emits a finding outside the shared contract."""


_REQUIRED_FIELDS = {
    "conversation_id",
    "workflow",
    "detector",
    "failure_type",
    "description",
    "evidence_turn_ids",
}


def detect_failures(conversation):
    """Run rule, judge, and behavioral detectors and preserve evidence as emitted."""
    turns = conversation.get("turns")
    if not isinstance(turns, list):
        raise FailureFindingError("conversation turns must be a list")
    valid_turn_ids = {turn.get("turn_id") for turn in turns if isinstance(turn, dict)}

    findings = (
        run_rule_based(conversation)
        + run_llm_judge(conversation)
        + run_behavioral(conversation)
    )
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise FailureFindingError(f"finding {index} must be an object")
        missing = _REQUIRED_FIELDS - finding.keys()
        if missing:
            raise FailureFindingError(
                f"finding {index} is missing fields: {', '.join(sorted(missing))}"
            )
        evidence_turn_ids = finding["evidence_turn_ids"]
        if not isinstance(evidence_turn_ids, list) or not evidence_turn_ids:
            raise FailureFindingError(f"finding {index} must include evidence turn IDs")
        unknown_turn_ids = [turn_id for turn_id in evidence_turn_ids if turn_id not in valid_turn_ids]
        if unknown_turn_ids:
            raise FailureFindingError(
                f"finding {index} references unknown turn IDs: {unknown_turn_ids}"
            )
    return findings