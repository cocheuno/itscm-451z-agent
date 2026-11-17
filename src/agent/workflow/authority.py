"""The incident authority. It approves a proposal only when the arguments are the rule's arguments."""

from __future__ import annotations

from agent.tools.writes import CLOSE_WORKAROUND
from agent.workflow.known_error import SIMILARITY_MIN

APPROVER = "incident authority"


def triage_decision(sys_id: str, category: str, impact: str, urgency: str, group: str) -> dict:
    return {
        "tool": "record_triage",
        "args": {
            "sys_id": sys_id,
            "category": category,
            "impact": str(impact),
            "urgency": str(urgency),
            "assignment_group": group,
            "rationale": (
                "incident authority approved record_triage. "
                "Rule: CI-class category and the CI service group."
            ),
        },
    }


def known_error_decision(
    sys_id: str,
    parent: str,
    comment: str,
    article_number: str,
    problem_number: str,
) -> dict:
    return {
        "tool": "apply_known_error",
        "args": {
            "sys_id": sys_id,
            "parent": parent,
            "comment": comment,
            "close_code": CLOSE_WORKAROUND,
            "close_notes": f"Workaround provided. Article {article_number}. Problem {problem_number}.",
            "rationale": (
                "incident authority approved apply_known_error. "
                f"Rule: published article {article_number} whose source is known-error "
                f"problem {problem_number}. Similarity threshold {SIMILARITY_MIN}."
            ),
        },
    }


def restore_decision(sys_id: str, close_code: str, close_notes: str) -> dict:
    return {
        "tool": "restore_service",
        "args": {
            "sys_id": sys_id,
            "close_code": close_code,
            "close_notes": close_notes,
            "rationale": (
                "incident authority approved restore_service. "
                "Rule: seeded close outcome. The resolver does not set On Hold."
            ),
        },
    }


def allows(tool: str, args: dict, decision: dict) -> bool:
    """True when this proposal is exactly the rule's tool and arguments."""
    return tool == decision["tool"] and args == decision["args"]


def run_approved(registry, audit, decision: dict) -> dict:
    """Propose the rule's arguments, approve them, and execute that proposal once."""
    tool = decision["tool"]
    args = decision["args"]
    pending = registry.dispatch(tool, args, audit=audit)
    proposal_id = pending["proposal_id"]
    stored = registry.approvals.get(proposal_id)
    if stored is None or not allows(stored.tool, stored.args, decision):
        if stored is not None and stored.status == "pending":
            registry.approvals.reject(proposal_id, APPROVER, "arguments differ from the rule")
        return {"status": "rejected", "proposal_id": proposal_id}
    registry.approvals.approve(proposal_id, APPROVER)
    result = registry.dispatch(tool, stored.args, approval_id=proposal_id, audit=audit)
    if isinstance(result, dict):
        result = {**result, "proposal_id": proposal_id, "approver": APPROVER}
    return result
