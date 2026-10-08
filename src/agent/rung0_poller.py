"""Rung 0: deterministic poller. Reads new incidents and applies keyword rules. No LLM.

    python -m agent.rung0_poller --since "2026-09-01 00:00:00" --dry-run
"""
from __future__ import annotations

import argparse

from agent.audit import AuditEntry, AuditLog

# TODO(student, Module 2): write 3-5 rules. Order matters; first match wins.
RULES: list[tuple[str, str, str]] = [
    # (keyword, category, assignment_group)
    ("vpn", "Network", "Network Ops"),
    ("password", "Inquiry / Help", "Service Desk L1"),
    ("printer", "Hardware", "Desktop Support"),
]


def classify_with_rules(ticket: dict) -> dict:
    text = (ticket.get("short_description", "") + " " + ticket.get("description", "")).lower()
    for kw, cat, group in RULES:
        if kw in text:
            return {"pred_category": cat, "pred_assignment_group": group, "rule": kw}
    return {"pred_category": None, "pred_assignment_group": None, "rule": None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="ISO timestamp watermark")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    from agent.analytics.predict import classify  # the served model; the LLM path is the bake-off's
    from agent.servicenow.client import ServiceNowClient

    sn = ServiceNowClient.from_env()
    log = AuditLog()
    for t in sn.new_incidents_since(a.since, ["sys_id", "number", "short_description", "description"]):
        pred = classify_with_rules(t)
        log.write(AuditEntry(ticket=t["number"], tool="rules", tier="read", inputs={"rule": pred["rule"]},
                             reasoning=f"keyword rule {pred['rule']}", outcome=str(pred)))
        suggestion = classify(t)
        log.write(AuditEntry(ticket=t["number"], tool="classify_incident", tier="read",
                             inputs={"model_version": suggestion["model_version"]},
                             reasoning="category model suggestion",
                             outcome=str({"pred_category": suggestion["pred_category"],
                                          "confidence": suggestion["confidence"]})))
        print(t["number"], pred, suggestion["pred_category"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
