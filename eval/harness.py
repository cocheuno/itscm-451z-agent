"""Eval harness stub.

Runs the held-out eval set through the current rung in dry-run mode (no writes) and reports metrics.
Exit code is non-zero when any metric is below eval/thresholds.yaml.

    python -m eval.harness --rung 1
    python -m eval.harness --rung auto --fixtures --report eval/reports/ci.json
    python -m eval.harness --summary eval/reports/ci.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from eval import metrics

ROOT = Path(__file__).resolve().parents[1]
EVAL_SET = ROOT / "data" / "eval" / "eval_set.jsonl"
OPEN_SET = ROOT / "data" / "eval" / "incidents_open.csv"
THRESH = ROOT / "eval" / "thresholds.yaml"
# The ticket fields an entry point may read. Ground truth (gt_*) is already in the eval set; these are the inputs.
INPUT_FIELDS = ("short_description", "description", "impact", "urgency", "contact_type")


def load_eval_set(path: Path = EVAL_SET, open_set: Path = OPEN_SET) -> list[dict]:
    """The holdout rows written by scripts/seed_pdi.py, joined on corpus_number to the ticket inputs.

    seed_pdi.py records sys_id, number, corpus_number and the gt_* columns; the inputs (impact, urgency,
    short_description, ...) come from data/eval/incidents_open.csv so the eval set never has to be re-seeded
    when an entry point needs another field.
    """
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if open_set.exists():
        import csv

        with open_set.open(newline="") as f:
            inputs = {r["number"]: {k: r[k] for k in INPUT_FIELDS if k in r} for r in csv.DictReader(f)}
        rows = [{**inputs.get(r.get("corpus_number"), {}), **r} for r in rows]
    return rows


def run_rung(rung: str, rows: list[dict], fixtures: bool) -> list[dict]:
    """Dispatch to the rung's entry point in dry-run mode. TODO(student): implement per rung.

    Each entry point must accept a ticket dict and return a dict with any of:
    pred_category, pred_priority, pred_assignment_group, and an 'audit' list of action records.
    """
    if rung == "auto":
        rung = detect_rung()
    if rung == "0":
        from agent.rung0_poller import classify_with_rules  # noqa: E402
        return [{**r, **classify_with_rules(r)} for r in rows]
    if rung == "1":
        from agent.analytics.predict import classify  # noqa: E402
        return [{**r, **classify(r)} for r in rows]
    raise NotImplementedError(f"rung {rung} entry point not wired into the harness yet")


def detect_rung() -> str:
    """Highest rung whose entry point exists. TODO(student): extend as rungs are added."""
    from agent.analytics.predict import available  # noqa: E402
    return "1" if available() else "0"


def compute(rows: list[dict]) -> dict:
    audit = [a for r in rows for a in r.get("audit", [])]
    return {
        "n": len(rows),
        "classification_accuracy": metrics.classification_accuracy(rows),
        "priority_sla_agreement": metrics.priority_sla_agreement(rows),
        "routing_accuracy": metrics.routing_accuracy(rows),
        "harmful_action_count": metrics.harmful_action_count(audit),
    }


def check(result: dict, thresholds: dict) -> list[str]:
    failures = []
    for k, want in thresholds.items():
        got = result.get(k)
        if got is None:
            continue
        bad = got > want if k == "harmful_action_count" else got < want
        if bad:
            failures.append(f"{k}: {got} vs threshold {want}")
    return failures


def summary(report: dict) -> str:
    lines = ["| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in report["metrics"].items()]
    if report["failures"]:
        lines.append("")
        lines += [f"- FAIL {f}" for f in report["failures"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rung", default="auto")
    ap.add_argument("--fixtures", action="store_true", help="use recorded ServiceNow responses (CI)")
    ap.add_argument("--report", default=None)
    ap.add_argument("--summary", default=None, help="print a Markdown summary of an existing report")
    a = ap.parse_args(argv)
    if a.summary:
        print(summary(json.loads(Path(a.summary).read_text())))
        return 0
    rows = load_eval_set()
    if not rows:
        print("eval set is empty; seed the PDI first (scripts/seed_pdi.py)")
        rows = []
    try:
        rows = run_rung(a.rung, rows, a.fixtures)
    except NotImplementedError as e:
        print(f"harness: {e}")
    m = compute(rows)
    thresholds = yaml.safe_load(THRESH.read_text()) if THRESH.exists() else {}
    failures = check(m, thresholds) if rows else []
    report = {"rung": a.rung, "metrics": m, "failures": failures}
    if a.report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(json.dumps(report, indent=2))
    print(summary(report))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
