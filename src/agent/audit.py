"""Append-only audit log. One JSON object per line. Every agent action — including refusals — goes here."""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"


@dataclass
class AuditEntry:
    ticket: str
    tool: str
    tier: str
    inputs: dict
    reasoning: str
    outcome: str
    approval_id: str | None = None
    idempotency_key: str | None = None
    before_image: dict | None = None
    harmful: bool = False
    latency_ms: int | None = None
    cost_usd: float | None = None
    ts: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


def idempotency_key(tool: str, args: dict) -> str:
    return hashlib.sha256(json.dumps({"tool": tool, "args": args}, sort_keys=True).encode()).hexdigest()[:16]


class AuditLog:
    def __init__(self, path: Path | None = None) -> None:
        LOG_DIR.mkdir(exist_ok=True)
        self.path = path or LOG_DIR / "audit.jsonl"

    def write(self, entry: AuditEntry) -> None:
        with self.path.open("a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
