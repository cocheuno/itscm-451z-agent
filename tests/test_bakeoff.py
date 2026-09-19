"""scripts/bakeoff.py scores any classifier callable over eval rows and tabulates the result."""
from __future__ import annotations

import importlib.util
import sys

from .conftest import ROOT

spec = importlib.util.spec_from_file_location("bakeoff", ROOT / "scripts" / "bakeoff.py")
bakeoff = importlib.util.module_from_spec(spec)
sys.modules["bakeoff"] = bakeoff
spec.loader.exec_module(bakeoff)

ROWS = [{"gt_category": "Network", "short_description": "vpn down"},
        {"gt_category": "Network", "short_description": "wifi flaky"},
        {"gt_category": "Hardware", "short_description": "printer jam"},
        {"gt_category": "Software", "short_description": "erp crash"}]


def test_score_counts_accuracy_macro_f1_latency_and_cost():
    def fn(t):  # gets Network right, calls everything else Network, and reports a cost
        return {"pred_category": "Network", "cost_usd": 0.001}
    m = bakeoff.score(ROWS, fn)
    assert m["n"] == 4 and m["accuracy"] == 0.5 and m["unclassified"] == 0
    assert m["per_class_f1"] == {"Hardware": 0.0, "Network": 0.667, "Software": 0.0}
    assert m["macro_f1"] == round(0.667 / 3, 3)
    assert m["cost_usd_per_prediction"] == 0.001 and m["latency_ms"] >= 0


def test_unclassified_and_table():
    m = bakeoff.score(ROWS, lambda t: {"pred_category": None})
    assert m["unclassified"] == 4 and m["accuracy"] == 0.0
    out = bakeoff.table({"rules": m})
    assert out.startswith("| Row | n | Accuracy") and "| rules | 4 | 0.0 |" in out and "Per-class F1" in out


def test_rules_row_resolves_to_the_rung0_poller():
    fn = bakeoff.resolve("rules")
    assert fn({"short_description": "VPN drops", "description": ""})["pred_category"] == "Network"
