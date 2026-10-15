"""The approval queue: a proposal is approved by a named person for exactly its arguments, and spent once."""
from __future__ import annotations

import pytest

from agent.approvals import ApprovalQueue


@pytest.fixture
def queue(tmp_path):
    return ApprovalQueue(tmp_path / "approvals.jsonl")


ARGS = {"sys_id": "abc", "assignment_group": "Network Ops", "rationale": "VPN symptoms"}


def test_propose_then_approve_then_execute_is_one_record_with_three_states(queue):
    p = queue.propose("assign_incident", ARGS, "VPN symptoms")
    assert p.status == "pending" and queue.pending() == [p]
    approved = queue.approve(p.id, "T. Carone")
    assert approved.status == "approved" and approved.approver == "T. Carone" and queue.pending() == []
    assert queue.verify(p.id, "assign_incident", ARGS) is not None
    done = queue.mark_executed(p.id, "INC1")
    assert done.status == "executed" and done.note == "INC1"
    assert len(queue.all()) == 1  # three lines in the file, one proposal


def test_verify_refuses_pending_rejected_spent_other_tool_and_other_args(queue):
    p = queue.propose("assign_incident", ARGS)
    assert queue.verify(p.id, "assign_incident", ARGS) is None  # not approved yet
    assert queue.verify(None, "assign_incident", ARGS) is None
    assert queue.verify("nope", "assign_incident", ARGS) is None
    queue.approve(p.id, "T. Carone")
    assert queue.verify(p.id, "resolve_incident", ARGS) is None  # other tool
    assert queue.verify(p.id, "assign_incident", {**ARGS, "assignment_group": "Desktop Support"}) is None  # other args
    queue.mark_executed(p.id)
    assert queue.verify(p.id, "assign_incident", ARGS) is None  # spent
    r = queue.propose("assign_incident", ARGS)
    queue.reject(r.id, "T. Carone", "wrong group")
    assert queue.verify(r.id, "assign_incident", ARGS) is None and queue.get(r.id).note == "wrong group"


def test_transitions_require_the_right_prior_state(queue):
    p = queue.propose("add_comment", {"sys_id": "x", "comment": "hi"})
    with pytest.raises(ValueError):
        queue.mark_executed(p.id)  # never approved
    queue.approve(p.id, "T. Carone")
    with pytest.raises(ValueError):
        queue.approve(p.id, "T. Carone")  # already decided
    with pytest.raises(KeyError):
        queue.approve("missing", "T. Carone")


def test_cli_lists_approves_and_insists_on_a_name(queue, capsys, monkeypatch):
    from agent import approvals

    monkeypatch.setattr(approvals, "ApprovalQueue", lambda: queue)
    p = queue.propose("assign_incident", ARGS, "VPN symptoms")
    approvals.main([])
    assert p.id in capsys.readouterr().out
    with pytest.raises(SystemExit):
        approvals.main(["--approve", p.id])  # no --as
    approvals.main(["--approve", p.id, "--as", "T. Carone"])
    assert "approved by T. Carone" in capsys.readouterr().out
    approvals.main([])
    assert "no pending" in capsys.readouterr().out
