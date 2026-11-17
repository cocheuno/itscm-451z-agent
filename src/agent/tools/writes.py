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

INCIDENT_BEFORE_FIELDS = [
    "sys_id", "number", "state", "assignment_group", "close_code", "close_notes", "work_notes",
    "comments", "category", "impact", "urgency", "parent",
]
CLOSE_WORKAROUND = "Workaround provided"
STATE_RESOLVED = "6"
AGENT_NOTE = "[agent]"  # every text the agent writes starts with this so a human can tell it apart


def _status(exc: ServiceNowError) -> str:
    text = str(exc)
    marker = " -> "
    if marker not in text:
        return "none"
    return text.split(marker, 1)[1].split(":", 1)[0].strip() or "none"


def _incident(sn, sys_id: str) -> dict:
    try:
        row = sn.get(tables.INCIDENT, sys_id, INCIDENT_BEFORE_FIELDS)
    except ServiceNowError as exc:
        raise ToolError(f"incident was not found HTTP {_status(exc)}") from None
    if not row:
        raise ToolError(f"incident {sys_id} not found")
    return row


def _group_sys_id(sn, name: str) -> str:
    try:
        rows = sn.list(tables.USER_GROUP, f"name={name}", ["sys_id", "name"], limit=1)
    except ServiceNowError as exc:
        raise ToolError(f"assignment group was not readable HTTP {_status(exc)}") from None
    if not rows:
        raise ToolError(f"assignment group {name!r} does not exist")
    return rows[0]["sys_id"]


def _write(sn, row: dict, payload: dict, live: bool) -> dict:
    """The shared tail of every write tool: dry run returns the plan; live writes and returns the before-image."""
    before_image = {"table": tables.INCIDENT, "sys_id": row["sys_id"], "fields": {k: row.get(k, "") for k in payload}}
    if not live:
        return {"dry_run": True, "number": row.get("number", ""), "would_set": payload, "before_image": before_image}
    try:
        before, after = sn.update_with_before_image(tables.INCIDENT, row["sys_id"], payload)
    except ServiceNowError as exc:
        raise ToolError(f"incident update was refused HTTP {_status(exc)}") from None
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
    """Put the fields in before_image back the way they were: the rollback plan, executed."""
    fields = before_image["fields"]
    if not live:
        return {"dry_run": True, "would_set": fields}
    sn.update(before_image["table"], before_image["sys_id"], fields)
    return {"dry_run": False, "set": fields}


def record_triage(
    sn, sys_id: str, category: str, impact: str, urgency: str, assignment_group: str, rationale: str, *,
    live: bool = False,
) -> dict:
    """Set category, impact, urgency, and the assignment group. Priority is the platform lookup."""
    row = _incident(sn, sys_id)
    if not category:
        raise ToolError("category is empty")
    group = _group_sys_id(sn, assignment_group)
    return _write(sn, row, {
        "category": category,
        "impact": str(impact),
        "urgency": str(urgency),
        "assignment_group": group,
        "work_notes": f"{AGENT_NOTE} {rationale}",
    }, live)


def apply_known_error(
    sn, sys_id: str, parent: str, comment: str, close_code: str, close_notes: str, rationale: str, *,
    live: bool = False,
) -> dict:
    """Post the workaround, link the parent problem, and resolve. One write, so the note cannot reopen it."""
    row = _incident(sn, sys_id)
    if close_code != CLOSE_WORKAROUND:
        raise ToolError("close code is not Workaround provided")
    if not parent or not comment:
        raise ToolError("known-error resolve needs a parent and a comment")
    return _write(sn, row, {
        "parent": parent,
        "comments": f"{AGENT_NOTE} {comment}",
        "state": STATE_RESOLVED,
        "close_code": close_code,
        "close_notes": f"{AGENT_NOTE} {close_notes}",
        "work_notes": f"{AGENT_NOTE} {rationale}",
    }, live)


def restore_service(
    sn, sys_id: str, close_code: str, close_notes: str, rationale: str, *, live: bool = False,
) -> dict:
    """Resolve with the seeded outcome. This tool has no On Hold state and no hold reason."""
    row = _incident(sn, sys_id)
    if not close_code or not close_notes:
        raise ToolError("a seeded restore needs a close code and close notes")
    payload = {
        "state": STATE_RESOLVED,
        "close_code": close_code,
        "close_notes": f"{AGENT_NOTE} {close_notes}",
        "work_notes": f"{AGENT_NOTE} {rationale}",
    }
    return _write(sn, row, payload, live)


def bind_writes(registry, sn, live: bool | None = None) -> None:
    """Bind the write tools. live=None reads AGENT_MODE from .env (dry_run unless it says live)."""
    if live is None:
        from agent import config

        live = config.load().agent_mode == "live"
    registry.bind("assign_incident", lambda sys_id, assignment_group, rationale:
                  assign_incident(sn, sys_id, assignment_group, rationale, live=live))
    registry.bind("resolve_incident", lambda sys_id, close_code, close_notes:
                  resolve_incident(sn, sys_id, close_code, close_notes, live=live))
    registry.bind("add_comment", lambda sys_id, comment: add_comment(sn, sys_id, comment, live=live))
    registry.bind(
        "record_triage",
        lambda sys_id, category, impact, urgency, assignment_group, rationale:
        record_triage(sn, sys_id, category, impact, urgency, assignment_group, rationale, live=live),
    )
    registry.bind(
        "apply_known_error",
        lambda sys_id, parent, comment, close_code, close_notes, rationale:
        apply_known_error(sn, sys_id, parent, comment, close_code, close_notes, rationale, live=live),
    )
    registry.bind(
        "restore_service",
        lambda sys_id, close_code, close_notes, rationale:
        restore_service(sn, sys_id, close_code, close_notes, rationale, live=live),
    )
