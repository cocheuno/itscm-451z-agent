"""Tool registry: loads JSON schemas, enforces tiers at dispatch, logs every call.

Nothing a model says can change a tier. The only way to change a tier is to edit the schema file,
which requires an ADR and a governance.md update in the same PR.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
    def __init__(self) -> None:
        self.tools: dict[str, ToolSpec] = {}
        for p in sorted(SCHEMA_DIR.glob("*.json")):
            self.tools[p.stem] = ToolSpec(json.loads(p.read_text()))

    def bind(self, name: str, fn: Callable[..., Any]) -> None:
        self.tools[name].fn = fn

    def dispatch(self, name: str, args: dict, *, approval_id: str | None = None, audit=None) -> Any:
        """TODO(student): complete in Modules 5 (read), 8 (propose/approval), and 12 (hardening).

        Required behaviour:
        - READ: call fn and return the result.
        - PROPOSE: do NOT call fn; return a proposal record {tool, args} for the approval queue.
        - EXECUTE_WITH_APPROVAL: verify approval_id against approvals.py for exactly these args; otherwise refuse.
        - AUTONOMOUS: call fn.
        - Every branch writes an audit entry (including refusals, marked harmful=True when a write was attempted
          above its tier or without approval).
        """
        spec = self.tools[name]
        if spec.fn is None:
            raise RuntimeError(f"tool {name} is not bound")
        if spec.tier is Tier.READ:
            return spec.fn(**args)
        raise NotImplementedError(f"dispatch for tier {spec.tier.value} not implemented yet")
