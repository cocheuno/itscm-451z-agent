"""Write-tier tools against a fake client: target checks, dry run, before-image, rollback."""
from __future__ import annotations

import pytest

from agent.servicenow.client import ServiceNowError
from agent.tools import writes
from agent.tools.errors import ToolError

INC = {"sys_id": "abc", "number": "INC0010001", "state": "1", "assignment_group": "", "close_code": "",
       "close_notes": "", "work_notes": "", "comments": ""}
GROUPS = {"Network Ops": "g-net", "Desktop Support": "g-desk"}


class FakeSN:
    """get/list/update as the write tools use them, with the student's before-image method already written."""

    def __init__(self):
        self.rows = {"abc": dict(INC)}
        self.patches = []

    def get(self, table, sys_id, fields=None):
        if sys_id not in self.rows:
            raise ServiceNowError(f"GET {table}/{sys_id} -> 404")
        row = self.rows[sys_id]
        return {k: row.get(k, "") for k in fields} if fields else dict(row)

    def list(self, table, query="", fields=None, limit=100, offset=0):
        name = query.removeprefix("name=")
        return [{"sys_id": GROUPS[name], "name": name}] if name in GROUPS else []

    def update(self, table, sys_id, payload):
        self.patches.append((sys_id, payload))
        self.rows[sys_id].update(payload)
        return dict(self.rows[sys_id])

    def update_with_before_image(self, table, sys_id, payload):
        before = self.get(table, sys_id, list(payload))
        return before, self.update(table, sys_id, payload)


def test_dry_run_checks_everything_and_writes_nothing():
    sn = FakeSN()
    out = writes.assign_incident(sn, "abc", "Network Ops", "VPN symptoms", live=False)
    assert out["dry_run"] is True and out["number"] == "INC0010001"
    assert out["would_set"] == {"assignment_group": "g-net", "work_notes": "[agent] VPN symptoms"}
    assert out["before_image"] == {"table": "incident", "sys_id": "abc",
                                   "fields": {"assignment_group": "", "work_notes": ""}}
    assert sn.patches == []


def test_missing_incident_and_missing_group_are_tool_errors():
    sn = FakeSN()
    with pytest.raises(ToolError, match="not found"):
        writes.assign_incident(sn, "nope", "Network Ops", "x")
    with pytest.raises(ToolError, match="does not exist"):
        writes.assign_incident(sn, "abc", "Nobody", "x")
    assert sn.patches == []


def test_live_write_returns_the_before_image_and_the_new_values():
    sn = FakeSN()
    out = writes.assign_incident(sn, "abc", "Desktop Support", "printer", live=True)
    assert out["dry_run"] is False
    assert out["before_image"]["fields"] == {"assignment_group": "", "work_notes": ""}
    assert out["after"] == {"assignment_group": "g-desk", "work_notes": "[agent] printer"}
    assert sn.patches == [("abc", {"assignment_group": "g-desk", "work_notes": "[agent] printer"})]


def test_resolve_and_comment_set_the_fields_their_schemas_promise():
    sn = FakeSN()
    r = writes.resolve_incident(sn, "abc", "Solved (Permanently)", "renewed cert", live=True)
    assert r["set"] == {"state": "6", "close_code": "Solved (Permanently)", "close_notes": "[agent] renewed cert"}
    c = writes.add_comment(sn, "abc", "We are on it.", live=False)
    assert c["would_set"] == {"comments": "[agent] We are on it."}


def test_rollback_restores_the_before_image():
    sn = FakeSN()
    out = writes.assign_incident(sn, "abc", "Network Ops", "VPN", live=True)
    try:
        back = writes.rollback(sn, out["before_image"], live=True)
    except NotImplementedError:
        pytest.skip("rollback is written in Module 7 session 2")
    assert back["set"] == {"assignment_group": "", "work_notes": ""}
    assert sn.rows["abc"]["assignment_group"] == ""


def test_bind_writes_binds_the_three_tools_in_dry_run():
    from agent.approvals import ApprovalQueue
    from agent.tools.registry import Registry

    r = Registry(ApprovalQueue(__import__("pathlib").Path("/nonexistent/never-written.jsonl")))
    writes.bind_writes(r, FakeSN(), live=False)
    for name in ("assign_incident", "resolve_incident", "add_comment"):
        assert r.tools[name].fn is not None
    assert r.tools["add_comment"].fn("abc", "hello")["dry_run"] is True
