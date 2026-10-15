"""Rung 3, Module 7: the write-tier tools, implemented against the ServiceNow Table API.

Every function here changes a record in the PDI, so every one of them is held to the change-management
rules the registry enforces: it is only ever called through `Registry.dispatch`, at the tier its schema
declares, with an approval where the tier needs one, and it returns a **before-image** (the fields it is
about to change, as they were) so the change can be rolled back from the audit log.

Two guards live in the functions themselves, because they are about the target rather than the caller:
the incident must exist, and a named group must exist. Either failing raises ToolError, which the
registry records as a harmful attempt (ADR: a write against a nonexistent target is harmful even when
nothing changed).

`live=False` is the dry run: the function does every check and returns what it *would* write, and nothing
reaches the instance. `AGENT_MODE` in .env chooses; `bind_writes` reads it.

    from agent.tools.writes import bind_writes
    registry = Registry(); bind_writes(registry, ServiceNowClient.from_env())
    registry.dispatch("assign_incident", {...})            # queues a proposal
    registry.dispatch("assign_incident", {...}, approval_id=<id>)   # executes, if approved for these args
"""
from __future__ import annotations

from agent.servicenow import tables
from agent.servicenow.client import ServiceNowError
from agent.tools.errors import ToolError

INCIDENT_BEFORE_FIELDS = ["sys_id", "number", "state", "assignment_group", "close_code", "close_notes", "work_notes",
                          "comments"]
STATE_RESOLVED = "6"
AGENT_NOTE = "[agent]"  # every text the agent writes starts with this so a human can tell it apart


def _incident(sn, sys_id: str) -> dict:
    try:
        row = sn.get(tables.INCIDENT, sys_id, INCIDENT_BEFORE_FIELDS)
    except ServiceNowError as e:
        raise ToolError(f"incident {sys_id} not found: {e}") from e
    if not row:
        raise ToolError(f"incident {sys_id} not found")
    return row


def _group_sys_id(sn, name: str) -> str:
    rows = sn.list(tables.USER_GROUP, f"name={name}", ["sys_id", "name"], limit=1)
    if not rows:
        raise ToolError(f"assignment group {name!r} does not exist")
    return rows[0]["sys_id"]


def _write(sn, row: dict, payload: dict, live: bool) -> dict:
    """The shared tail of every write tool: dry run returns the plan; live writes and returns the before-image."""
    before_image = {"table": tables.INCIDENT, "sys_id": row["sys_id"], "fields": {k: row.get(k, "") for k in payload}}
    if not live:
        return {"dry_run": True, "number": row.get("number", ""), "would_set": payload, "before_image": before_image}
    before, after = sn.update_with_before_image(tables.INCIDENT, row["sys_id"], payload)
    before_image["fields"] = before
    return {"dry_run": False, "number": row.get("number", ""), "set": payload, "before_image": before_image,
            "after": {k: after.get(k, "") for k in payload}}


def assign_incident(sn, sys_id: str, assignment_group: str, rationale: str, *, live: bool = False) -> dict:
    """Set the assignment group and leave the rationale in the work notes (internal, not customer-visible)."""
    row = _incident(sn, sys_id)
    group = _group_sys_id(sn, assignment_group)
    return _write(sn, row, {"assignment_group": group, "work_notes": f"{AGENT_NOTE} {rationale}"}, live)


def resolve_incident(sn, sys_id: str, close_code: str, close_notes: str, *, live: bool = False) -> dict:
    """Move the incident to Resolved with a close code and notes. The requester can reopen it; closing is the
    instance's job after its own timer, never the agent's."""
    row = _incident(sn, sys_id)
    return _write(sn, row, {"state": STATE_RESOLVED, "close_code": close_code,
                            "close_notes": f"{AGENT_NOTE} {close_notes}"}, live)


def add_comment(sn, sys_id: str, comment: str, *, live: bool = False) -> dict:
    """Append a customer-visible comment. Visible to the requester, so the output filter (Module 12) applies."""
    row = _incident(sn, sys_id)
    return _write(sn, row, {"comments": f"{AGENT_NOTE} {comment}"}, live)


def rollback(sn, before_image: dict, *, live: bool = False) -> dict:
    """TODO(student, Module 7 session 2): put the fields in before_image back the way they were.

    before_image is what every write tool returns and what the audit entry stores:
    {"table": "incident", "sys_id": "...", "fields": {"assignment_group": "<old sys_id>", ...}}.
    Dry run returns {"dry_run": True, "would_set": fields}; live PATCHes the fields and returns
    {"dry_run": False, "set": fields}. Exact code in lecture 07b.
    """
    raise NotImplementedError


def bind_writes(registry, sn, live: bool | None = None) -> None:
    """Bind the three write tools. live=None reads AGENT_MODE from .env (dry_run unless it says live)."""
    if live is None:
        from agent import config

        live = config.load().agent_mode == "live"
    registry.bind("assign_incident", lambda sys_id, assignment_group, rationale:
                  assign_incident(sn, sys_id, assignment_group, rationale, live=live))
    registry.bind("resolve_incident", lambda sys_id, close_code, close_notes:
                  resolve_incident(sn, sys_id, close_code, close_notes, live=live))
    registry.bind("add_comment", lambda sys_id, comment: add_comment(sn, sys_id, comment, live=live))
