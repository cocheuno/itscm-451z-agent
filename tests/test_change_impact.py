"""Change-impact analysis on a toy history: a flat baseline of 10 tickets a day, then a burst."""
from __future__ import annotations

import pandas as pd
import pytest

from agent.analytics import change_impact as ci

END = pd.Timestamp("2026-06-16 22:30:00")


def toy_history() -> pd.DataFrame:
    """10 tickets per day for 70 days around END (8 Network, 2 Software), plus 40 extra Network tickets in the
    24 hours after END."""
    rows = []
    for d in range(-60, 10):
        for k in range(10):
            rows.append({"opened_at": END + pd.Timedelta(days=d, hours=k), "category": "Network" if k < 8 else "Software"})
    for k in range(40):
        rows.append({"opened_at": END + pd.Timedelta(minutes=30 + k * 30), "category": "Network"})
    return pd.DataFrame(rows)


def test_observed_count_is_the_window_after_the_change():
    h = toy_history()
    assert ci.observed_count(h, END, hours=72) == 30 + 40
    assert ci.observed_count(h, END, hours=72, category="Software") == 6


def test_expected_count_is_the_baseline_rate_times_the_window():
    h = toy_history()
    try:
        e = ci.expected_count(h, END, hours=72, baseline_days=28)
    except NotImplementedError:
        pytest.skip("expected_count is written in Module 8 session 1")
    assert e == pytest.approx(30.0)
    assert ci.expected_count(h, END, hours=72, baseline_days=28, category="Network") == pytest.approx(24.0)


def test_surprise_is_zero_for_a_burst_and_high_for_normal_volume():
    h = toy_history()
    assert ci.surprise(h, END, observed=70, hours=72, baseline_days=28) == 0.0
    assert ci.surprise(h, END, observed=30, hours=72, baseline_days=28) == 1.0


def test_impact_table_ranks_the_burst_first():
    h = toy_history()
    changes = pd.DataFrame({"number": ["CHG1", "CHG2"], "cmdb_ci": ["SW-1", "DB-1"],
                            "end": [END, END - pd.Timedelta(days=14)]})
    try:
        t = ci.impact_table(h, changes)
    except NotImplementedError:
        pytest.skip("expected_count is written in Module 8 session 1")
    assert list(t["number"]) == ["CHG1", "CHG2"]
    top = t.iloc[0]
    assert top["observed"] == 70 and top["ratio"] == pytest.approx(70 / 30, abs=0.01)
    assert top["top_category"] == "Network" and top["surprise"] == 0.0
    assert t.iloc[1]["ratio"] == pytest.approx(1.0, abs=0.01)
