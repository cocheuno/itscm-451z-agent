"""A1 bake-off: run every available classifier over the holdout eval set and print one comparison table.

    python scripts/bakeoff.py                      # rules + every trained model version (+ LLM if implemented)
    python scripts/bakeoff.py --rows rules,lr:0.1,gbm:0.2,llm
    python scripts/bakeoff.py --report eval/reports/bakeoff.json

Rows: "rules" is the Rung 0 keyword poller; "<label>:<version>" is a model under src/agent/models/ loaded
through agent.analytics.predict; "llm" is agent.analytics.llm_classify.classify (Module 4, student-written).
Every row reports accuracy, macro F1, per-class F1, latency per prediction, and cost per prediction (zero for
local models; the LLM row sums what the API reported). The eval set is the same one the harness scores, so the
numbers here and in `python -m eval.harness` agree.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from eval import harness  # noqa: E402

import agent.config  # noqa: E402,F401  (loads .env so ANTHROPIC_API_KEY is visible to available_rows)

Classifier = Callable[[dict], dict]


def available_rows() -> list[str]:
    from agent.analytics import predict

    rows = ["rules"] + [f"model:{v}" for v in predict.versions()]
    if os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-ant-") and "..." not in os.getenv("ANTHROPIC_API_KEY", ""):
        rows.append("llm")  # only when a real key is configured; pass --rows llm to force it
    return rows


def resolve(row: str) -> Classifier:
    if row == "rules":
        from agent.rung0_poller import classify_with_rules
        return classify_with_rules
    if row == "llm":
        from agent.analytics.llm_classify import classify
        return classify
    label, _, version = row.partition(":")
    from agent.analytics import predict
    return lambda t: predict.classify(t, version=version or None)


def score(rows: list[dict], fn: Classifier) -> dict:
    labels = sorted({r["gt_category"] for r in rows})
    preds, latencies, cost = [], [], 0.0
    for r in rows:
        t0 = time.perf_counter()
        out = fn(r)
        latencies.append((time.perf_counter() - t0) * 1000)
        preds.append(out.get("pred_category"))
        cost += float(out.get("cost_usd") or 0.0)
    truth = [r["gt_category"] for r in rows]
    per_class = {}
    for lab in labels:
        tp = sum(p == lab and t == lab for p, t in zip(preds, truth, strict=True))
        fp = sum(p == lab and t != lab for p, t in zip(preds, truth, strict=True))
        fn_ = sum(p != lab and t == lab for p, t in zip(preds, truth, strict=True))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn_) if tp + fn_ else 0.0
        per_class[lab] = round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0
    return {
        "n": len(rows),
        "accuracy": round(sum(p == t for p, t in zip(preds, truth, strict=True)) / len(rows), 3),
        "macro_f1": round(sum(per_class.values()) / len(labels), 3),
        "per_class_f1": per_class,
        "latency_ms": round(sum(latencies) / len(latencies), 2),
        "cost_usd_per_prediction": round(cost / len(rows), 6),
        "unclassified": sum(p is None for p in preds),
    }


def table(results: dict[str, dict]) -> str:
    lines = ["| Row | n | Accuracy | Macro F1 | Latency ms | Cost $/pred | Unclassified |", "|---|---|---|---|---|---|---|"]
    for row, m in results.items():
        lines.append(f"| {row} | {m['n']} | {m['accuracy']} | {m['macro_f1']} | {m['latency_ms']} | "
                     f"{m['cost_usd_per_prediction']} | {m['unclassified']} |")
    labels = sorted({lab for m in results.values() for lab in m["per_class_f1"]})
    lines += ["", "Per-class F1:", "| Row | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
    for row, m in results.items():
        lines.append(f"| {row} | " + " | ".join(str(m["per_class_f1"].get(lab, "")) for lab in labels) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", default=None, help="comma-separated rows; default: everything available")
    ap.add_argument("--report", default=None, help="write the results as JSON here")
    a = ap.parse_args(argv)
    rows = harness.load_eval_set()
    if not rows:
        print("eval set is empty; seed the PDI first (scripts/seed_pdi.py)")
        return 1
    wanted = a.rows.split(",") if a.rows else available_rows()
    results = {row: score(rows, resolve(row)) for row in wanted}
    print(table(results))
    if a.report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
