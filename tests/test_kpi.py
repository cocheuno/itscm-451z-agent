"""KPI functions on the committed history: the numbers the lectures quote."""
from __future__ import annotations

import pandas as pd
import pytest

from agent.analytics import kpi
from agent.analytics.features import load_history


@pytest.fixture(scope="module")
def history():
    return load_history()


def test_mttr_overall_and_by_category(history):
    overall = kpi.mttr(history)
    assert overall.loc["all", "tickets"] == 4242
    assert 400 < overall.loc["all", "median_min"] < 450 < overall.loc["all", "mean_min"]
    by_cat = kpi.mttr(history, "category")
    assert by_cat["tickets"].sum() == 4242 and by_cat.loc["Hardware", "median_min"] > by_cat.loc["Security", "median_min"]


def test_hardware_gets_slower_every_month(history):
    t = kpi.mttr_by_month(history)
    hw = t["Hardware"].tolist()
    assert hw == sorted(hw) and hw[0] < 700 and hw[-1] > 2700


def test_sla_attainment_falls_with_priority(history):
    t = kpi.sla_attainment(history)
    assert list(t.index) == [1, 2, 3, 4, 5]
    assert t["attainment"].is_monotonic_increasing and t["tickets"].sum() == 4242


def test_pareto_sums_to_one_and_leads_with_inquiry(history):
    t = kpi.category_pareto(history)
    assert t.index[0] == "Inquiry / Help" and t["tickets"].iloc[0] == 1223
    assert abs(t["cumulative"].iloc[-1] - 1.0) < 0.01


def test_backlog_aging_buckets_cover_every_open_ticket():
    o = pd.DataFrame({"opened_at": pd.to_datetime(["2026-09-08 12:00", "2026-09-07 12:00", "2026-09-03 00:00"])})
    t = kpi.backlog_aging(o)
    assert t["tickets"].sum() == 3 and t.loc["0-1 days", "tickets"] == 2 and t.loc["4-7 days", "tickets"] == 1
    assert kpi.backlog_aging(kpi.load_open_set())["tickets"].sum() == 150
