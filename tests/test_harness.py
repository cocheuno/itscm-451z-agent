"""eval/harness.py: the eval set is joined to the ticket inputs, and metrics/thresholds behave."""
from __future__ import annotations

import json

from eval import harness


def test_load_eval_set_joins_ticket_inputs_from_the_open_set(tmp_path):
    ev = tmp_path / "eval_set.jsonl"
    ev.write_text(json.dumps({"sys_id": "x", "number": "INC1", "corpus_number": "SYN0004243", "holdout": True,
                              "gt_category": "Network", "description": "d"}) + "\n")
    rows = harness.load_eval_set(ev)  # default open set: data/eval/incidents_open.csv
    assert len(rows) == 1
    r = rows[0]
    assert r["gt_category"] == "Network" and r["corpus_number"] == "SYN0004243"  # eval-set fields win
    assert set(harness.INPUT_FIELDS) <= set(r)  # inputs joined in
    assert r["impact"] in {"1", "2", "3"} and r["urgency"] in {"1", "2", "3"}


def test_load_eval_set_without_open_set_or_file(tmp_path):
    assert harness.load_eval_set(tmp_path / "missing.jsonl") == []
    ev = tmp_path / "eval_set.jsonl"
    ev.write_text(json.dumps({"corpus_number": "SYN0004243", "gt_category": "Network"}) + "\n")
    assert harness.load_eval_set(ev, open_set=tmp_path / "nope.csv") == [{"corpus_number": "SYN0004243",
                                                                            "gt_category": "Network"}]


def test_check_flags_only_metrics_below_threshold():
    m = {"classification_accuracy": 0.9, "priority_sla_agreement": 0.5, "harmful_action_count": 0}
    fails = harness.check(m, {"classification_accuracy": 0.8, "priority_sla_agreement": 0.9,
                              "harmful_action_count": 0, "routing_accuracy": 0.75})
    assert fails == ["priority_sla_agreement: 0.5 vs threshold 0.9"]  # absent metrics are not failures


def test_priority_agreement_compares_int_predictions_to_text_truth():
    from eval import metrics

    rows = [{"pred_priority": 3, "gt_priority": "3"}, {"pred_priority": None, "gt_priority": "2"},
            {"pred_priority": "1", "gt_priority": "1"}]
    assert metrics.priority_sla_agreement(rows) == 2 / 3


def test_eval_set_path_prefers_the_local_seeded_copy(tmp_path):
    local, committed = tmp_path / "local.jsonl", tmp_path / "committed.jsonl"
    assert harness.eval_set_path(local, committed) == committed  # nothing seeded yet
    local.write_text("")
    assert harness.eval_set_path(local, committed) == local
