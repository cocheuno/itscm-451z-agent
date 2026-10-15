"""Tool registry: loads JSON schemas, enforces tiers at dispatch, logs every call.

Nothing a model says can change a tier. The only way to change a tier is to edit the schema file,
which requires an ADR and a governance.md update in the same PR.

Dispatch is the one door every tool call goes through, and the tier decides what happens at the door:

- read: call the function.
- propose: never call the function; write a proposal to the approval queue and return it.
- execute_with_approval: with no approval id, behave like propose. With one, verify it names an approved
  proposal for this tool and exactly these arguments that has not been spent; then call the function and
  mark the proposal executed. Anything else is refused and recorded as harmful.
- autonomous: call the function (no tool has this tier yet; granting it needs an ADR).

Every branch writes an audit entry when an AuditLog is passed, refusals included. A refusal is marked
harmful when a write was attempted with a missing, mismatched or reused approval, or against a target that
does not exist (ToolError). eval/metrics.harmful_action_count counts those entries; the threshold is zero.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent.approvals import ApprovalQueue
from agent.audit import AuditEntry, idempotency_key
from agent.tools.errors import ApprovalRefused, ToolError
from agent.tools.tiers import Tier

SCHEMA_DIR = Path(__file__).parent / "schemas"


class ToolSpec:
    def __init__(self, schema: dict, fn: Callable[..., Any] | None = None) -> None:
        self.name: str = schema["name"]
        self.description: str = schema["description"]
        self.input_schema: dict = schema["input_schema"]
        self.tier = Tier(schema["action_tier"])
        self.fn = fn

    def as_llm_tool(self) -> dict:
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


class Registry:
    def __init__(self, approvals: ApprovalQueue | None = None) -> None:
        self.tools: dict[str, ToolSpec] = {}
        for p in sorted(SCHEMA_DIR.glob("*.json")):
            self.tools[p.stem] = ToolSpec(json.loads(p.read_text(encoding="utf-8")))
        self.approvals = approvals or ApprovalQueue()

    def bind(self, name: str, fn: Callable[..., Any]) -> None:
        self.tools[name].fn = fn

    def dispatch(self, name: str, args: dict, *, approval_id: str | None = None, audit=None,
                 ticket: str = "") -> Any:
        """Call a tool at its tier. See the module docstring for what each tier does at this door."""
        spec = self.tools[name]
        if spec.fn is None:
            raise RuntimeError(f"tool {name} is not bound")
        ticket = ticket or str(args.get("sys_id") or args.get("number") or "")
        key = idempotency_key(name, args)

        def log(outcome: str, reasoning: str, *, harmful: bool = False, before_image: dict | None = None) -> None:
            if audit is not None:
                audit.write(AuditEntry(ticket=ticket, tool=name, tier=spec.tier.value, inputs=args, reasoning=reasoning,
                                       outcome=outcome, approval_id=approval_id, idempotency_key=key,
                                       before_image=before_image, harmful=harmful))

        if spec.tier is Tier.READ:
            result = spec.fn(**args)
            log("ok", "read tier: no approval needed")
            return result

        if spec.tier is Tier.PROPOSE or (spec.tier is Tier.EXECUTE_WITH_APPROVAL and approval_id is None):
            reason = str(args.get("rationale") or args.get("comment") or args.get("close_notes") or "")
            p = self.approvals.propose(name, args, reason)
            log(f"proposed {p.id}", f"{spec.tier.value} tier: queued for a human decision, nothing written")
            return {"status": "pending", "proposal_id": p.id, "tool": name, "args": args}

        if spec.tier is Tier.EXECUTE_WITH_APPROVAL:
            p = self.approvals.verify(approval_id, name, args)
            if p is None:
                log("refused", "approval id missing, for other arguments, or already spent", harmful=True)
                raise ApprovalRefused(f"{name}: no valid approval {approval_id!r} for these arguments")
            result = self._run(spec, args, log)
            self.approvals.mark_executed(p.id, note=str(result.get("number", "")) if isinstance(result, dict) else "")
            return result

        return self._run(spec, args, log)  # autonomous

    @staticmethod
    def _run(spec: ToolSpec, args: dict, log: Callable[..., None]) -> Any:
        try:
            result = spec.fn(**args)
        except ToolError as e:
            log(f"refused: {e}", "write against a target the tool could not find", harmful=True)
            raise
        before = result.get("before_image") if isinstance(result, dict) else None
        dry = isinstance(result, dict) and result.get("dry_run")
        log("dry run: nothing written" if dry else "executed", f"{spec.tier.value} tier", before_image=before)
        return result
