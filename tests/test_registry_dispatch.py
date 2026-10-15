"""Registry.dispatch: the tier decides what happens at the door, and every branch leaves an audit entry."""
from __future__ import annotations

import pytest
from eval import metrics

from agent.approvals import ApprovalQueue
from agent.audit import AuditLog
from agent.tools.errors import ApprovalRefused, ToolError
from agent.tools.registry import Registry
from agent.tools.tiers import Tier

ARGS = {"sys_id": "abc", "assignment_group": "Network Ops", "rationale": "VPN symptoms"}


@pytest.fixture
def world(tmp_path):
    registry = Registry(ApprovalQueue(tmp_path / "approvals.jsonl"))
    audit = AuditLog(tmp_path / "audit.jsonl")
    calls = []
    registry.bind("lookup_ci", lambda name: calls.append(("lookup_ci", name)) or {"found": True, "name": name})
    registry.bind("add_comment", lambda sys_id, comment: calls.append(("add_comment", sys_id)) or {"dry_run": True})
    registry.bind("assign_incident", lambda sys_id, assignment_group, rationale:
                  calls.append(("assign_incident", sys_id)) or {"dry_run": False, "number": "INC1",
                                                                "before_image": {"table": "incident", "sys_id": sys_id,
                                                                                 "fields": {"assignment_group": ""}}})
    return registry, audit, calls


def test_read_tier_calls_and_audits_without_approval(world):
    registry, audit, calls = world
    assert registry.dispatch("lookup_ci", {"name": "VPN-GW-01"}, audit=audit)["found"]
    assert calls == [("lookup_ci", "VPN-GW-01")]
    (e,) = audit.read()
    assert e["tool"] == "lookup_ci" and e["tier"] == "read" and e["outcome"] == "ok" and not e["harmful"]


def test_propose_tier_never_calls_the_function(world):
    registry, audit, calls = world
    out = registry.dispatch("add_comment", {"sys_id": "abc", "comment": "hi"}, audit=audit)
    assert out["status"] == "pending" and calls == []
    assert registry.approvals.get(out["proposal_id"]).reason == "hi"
    (e,) = audit.read()
    assert e["outcome"].startswith("proposed") and not e["harmful"]


def test_execute_with_approval_without_an_id_is_a_proposal(world):
    registry, audit, calls = world
    out = registry.dispatch("assign_incident", ARGS, audit=audit)
    assert out["status"] == "pending" and calls == [] and registry.approvals.pending()


def test_approved_proposal_executes_once_and_stores_the_before_image(world):
    registry, audit, calls = world
    pid = registry.dispatch("assign_incident", ARGS, audit=audit)["proposal_id"]
    registry.approvals.approve(pid, "T. Carone")
    out = registry.dispatch("assign_incident", ARGS, approval_id=pid, audit=audit)
    assert out["number"] == "INC1" and calls == [("assign_incident", "abc")]
    assert registry.approvals.get(pid).status == "executed"
    done = audit.read()[-1]
    assert done["outcome"] == "executed" and done["approval_id"] == pid
    assert done["before_image"]["fields"] == {"assignment_group": ""}
    with pytest.raises(ApprovalRefused):  # the same approval cannot be spent twice
        registry.dispatch("assign_incident", ARGS, approval_id=pid, audit=audit)
    assert calls == [("assign_incident", "abc")]
    assert metrics.harmful_action_count(audit.read()) == 1


def test_forged_or_mismatched_approval_is_refused_and_harmful(world):
    registry, audit, calls = world
    pid = registry.dispatch("assign_incident", ARGS, audit=audit)["proposal_id"]
    registry.approvals.approve(pid, "T. Carone")
    with pytest.raises(ApprovalRefused):
        registry.dispatch("assign_incident", {**ARGS, "assignment_group": "Desktop Support"}, approval_id=pid,
                          audit=audit)
    with pytest.raises(ApprovalRefused):
        registry.dispatch("assign_incident", ARGS, approval_id="made-up", audit=audit)
    assert calls == []
    assert metrics.harmful_action_count(audit.read()) == 2
    assert registry.approvals.get(pid).status == "approved"  # still spendable for the right arguments


def test_tool_error_on_an_approved_write_is_recorded_as_harmful(world):
    registry, audit, calls = world

    def missing(sys_id, assignment_group, rationale):
        raise ToolError("incident nope not found")

    registry.bind("assign_incident", missing)
    pid = registry.dispatch("assign_incident", ARGS, audit=audit)["proposal_id"]
    registry.approvals.approve(pid, "T. Carone")
    with pytest.raises(ToolError):
        registry.dispatch("assign_incident", ARGS, approval_id=pid, audit=audit)
    last = audit.read()[-1]
    assert last["harmful"] and last["outcome"].startswith("refused")


def test_no_schema_is_autonomous_yet():
    assert all(spec.tier is not Tier.AUTONOMOUS for spec in Registry().tools.values())


def test_dispatch_without_an_audit_log_still_enforces_the_tier(world):
    registry, _, calls = world
    out = registry.dispatch("assign_incident", ARGS)
    assert out["status"] == "pending" and calls == []
