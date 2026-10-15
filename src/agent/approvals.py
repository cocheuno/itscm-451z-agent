"""Proposals and approvals for the write-tier tools (Rung 3, Modules 7 and 8).

ITIL change management in one paragraph: nobody changes a production system on the spot. The change is
written down first (what, why, to which record), somebody with the authority says yes, and only then is it
made, with a way back if it goes wrong. The agent follows the same shape. A **proposal** is a tool call
that has not happened yet: tool name, arguments, the reason. An **approval** is a named person saying yes
to exactly that proposal. The registry executes an `execute_with_approval` tool only when it is handed the
id of an approved proposal whose arguments match, and it marks the proposal executed so the same approval
cannot be spent twice.

Storage is one JSON object per line in logs/approvals.jsonl, append-only like the audit log: a proposal's
current state is its last line. The file is git-ignored (logs/); it is per machine.

    python -m agent.approvals                         # list pending proposals
    python -m agent.approvals --approve <id> --as "T. Carone"
    python -m agent.approvals --reject <id> --as "T. Carone" --why "wrong group"
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from agent.audit import LOG_DIR, idempotency_key

STATUSES = ("pending", "approved", "rejected", "executed")


@dataclass
class Proposal:
    tool: str
    args: dict
    reason: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    idempotency_key: str = ""
    status: str = "pending"
    requested_at: float = field(default_factory=time.time)
    approver: str | None = None
    decided_at: float | None = None
    executed_at: float | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.idempotency_key:
            self.idempotency_key = idempotency_key(self.tool, self.args)


class ApprovalQueue:
    """The approval queue. Every state change appends a line; reading replays the lines, last one wins."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or LOG_DIR / "approvals.jsonl"

    # ---- storage ----------------------------------------------------------
    def _append(self, p: Proposal) -> Proposal:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(p)) + "\n")
        return p

    def all(self) -> dict[str, Proposal]:
        if not self.path.exists():
            return {}
        out: dict[str, Proposal] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                p = Proposal(**json.loads(line))
                out[p.id] = p
        return out

    def get(self, proposal_id: str) -> Proposal | None:
        return self.all().get(proposal_id)

    def pending(self) -> list[Proposal]:
        return [p for p in self.all().values() if p.status == "pending"]

    # ---- the four transitions --------------------------------------------
    def propose(self, tool: str, args: dict, reason: str = "") -> Proposal:
        return self._append(Proposal(tool=tool, args=args, reason=reason))

    def approve(self, proposal_id: str, approver: str) -> Proposal:
        p = self._require(proposal_id, "pending")
        p.status, p.approver, p.decided_at = "approved", approver, time.time()
        return self._append(p)

    def reject(self, proposal_id: str, approver: str, why: str = "") -> Proposal:
        p = self._require(proposal_id, "pending")
        p.status, p.approver, p.decided_at, p.note = "rejected", approver, time.time(), why
        return self._append(p)

    def verify(self, approval_id: str | None, tool: str, args: dict) -> Proposal | None:
        """The approved proposal this approval id names, if it is for exactly this tool and these arguments
        and has not been executed yet; otherwise None. The registry refuses on None."""
        if not approval_id:
            return None
        p = self.get(approval_id)
        if p is None or p.status != "approved" or p.tool != tool:
            return None
        if p.idempotency_key != idempotency_key(tool, args):
            return None
        return p

    def mark_executed(self, proposal_id: str, note: str = "") -> Proposal:
        p = self._require(proposal_id, "approved")
        p.status, p.executed_at, p.note = "executed", time.time(), note
        return self._append(p)

    def _require(self, proposal_id: str, status: str) -> Proposal:
        p = self.get(proposal_id)
        if p is None:
            raise KeyError(f"no proposal {proposal_id}")
        if p.status != status:
            raise ValueError(f"proposal {proposal_id} is {p.status}, not {status}")
        return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="list, approve or reject the agent's proposals")
    ap.add_argument("--approve", metavar="ID")
    ap.add_argument("--reject", metavar="ID")
    ap.add_argument("--as", dest="approver", metavar="NAME", help="who is deciding; recorded on the proposal")
    ap.add_argument("--why", default="", help="reason for a rejection")
    ap.add_argument("--all", action="store_true", help="list every proposal, not only the pending ones")
    a = ap.parse_args(argv)
    q = ApprovalQueue()
    if a.approve or a.reject:
        if not a.approver:
            ap.error("--as NAME is required: approvals are made by a named person")
        p = q.approve(a.approve, a.approver) if a.approve else q.reject(a.reject, a.approver, a.why)
        print(f"{p.id} {p.status} by {p.approver}: {p.tool} {json.dumps(p.args)}")
        return 0
    rows = list(q.all().values()) if a.all else q.pending()
    if not rows:
        print("no pending proposals" if not a.all else "no proposals")
        return 0
    for p in rows:
        print(f"{p.id}  {p.status:9}  {p.tool:18}  {json.dumps(p.args)}  reason: {p.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
