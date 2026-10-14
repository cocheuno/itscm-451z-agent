"""Descriptive KPIs of the service desk, computed from the closed-incident history (Rung 2, folded into Module 8).

These are the numbers a desk manager asks for every Monday. Each function takes the history DataFrame from
agent.analytics.features.load_history() and returns a small table. They are deliberately plain pandas so a
reader can follow every step; nothing is trained. Module 8 uses them as the baseline the change-impact
analysis is measured against, and the Rung 2 agent narrates them in its health report.

    python -m agent.analytics.kpi          # prints the five tables

Definitions (docs/sla.md has the SLA clock):
- MTTR, mean time to resolve: resolve_minutes from opened_at to resolved_at. The median is reported next to the
  mean because a few very slow tickets drag the mean up (the mean here is four times the median).
- SLA attainment: share of tickets with made_sla true, by priority.
- Backlog aging: how long the open tickets have been waiting, in buckets.
- Category Pareto: tickets per category with the cumulative share, so the few categories that make most of the
  work are visible.
"""
from __future__ import annotations

import pandas as pd

from agent.analytics.features import ROOT, load_history

OPEN_SET = ROOT / "data" / "eval" / "incidents_open.csv"
AGE_BUCKETS = [-1, 1, 3, 7, 14, 10**6]
AGE_LABELS = ["0-1 days", "2-3 days", "4-7 days", "8-14 days", "over 14 days"]


def mttr(history: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    """Median and mean resolve minutes, overall or per value of `by` (for example "category" or "priority")."""
    if by is None:
        s = history["resolve_minutes"]
        return pd.DataFrame({"median_min": [s.median()], "mean_min": [s.mean()], "tickets": [len(s)]}, index=["all"])
    g = history.groupby(by)["resolve_minutes"]
    return pd.DataFrame({"median_min": g.median(), "mean_min": g.mean(), "tickets": g.size()})


def mttr_by_month(history: pd.DataFrame, by: str = "category") -> pd.DataFrame:
    """Median resolve minutes per month (rows) and category (columns). A column that climbs month over month
    is a category getting slower; the Module 2 notebook saw Hardware do exactly that."""
    month = history["opened_at"].dt.to_period("M").astype(str)
    return history.groupby([month, by])["resolve_minutes"].median().unstack(by).round(0)


def sla_attainment(history: pd.DataFrame) -> pd.DataFrame:
    """Share of tickets that met their SLA, by priority, with the counts the share is made of."""
    g = history.groupby("priority")["made_sla"]
    return pd.DataFrame({"attainment": g.mean().round(3), "met": g.sum(), "tickets": g.size()})


def backlog_aging(open_set: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    """Open tickets by age bucket. `as_of` defaults to the newest open ticket's time, so the table describes the
    backlog as it stood when the snapshot was taken rather than how stale the file is today."""
    when = as_of or open_set["opened_at"].max()
    age_days = (when - open_set["opened_at"]).dt.total_seconds() / 86400
    bucket = pd.cut(age_days, AGE_BUCKETS, labels=AGE_LABELS)
    counts = bucket.value_counts().reindex(AGE_LABELS, fill_value=0)
    return pd.DataFrame({"tickets": counts, "share": (counts / len(open_set)).round(3)})


def category_pareto(history: pd.DataFrame, by: str = "category") -> pd.DataFrame:
    """Tickets per category, largest first, with the running share of all tickets."""
    counts = history[by].value_counts()
    share = counts / counts.sum()
    return pd.DataFrame({"tickets": counts, "share": share.round(3), "cumulative": share.cumsum().round(3)})


def load_open_set(path=OPEN_SET) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["opened_at"])


def main() -> int:
    pd.set_option("display.width", 140)
    h = load_history()
    print(f"history: {len(h)} closed incidents, {h['opened_at'].min().date()} to {h['opened_at'].max().date()}\n")
    print("MTTR overall (minutes)\n", mttr(h).round(1), "\n")
    print("MTTR by category\n", mttr(h, "category").round(0), "\n")
    print("Median resolve minutes by month and category\n", mttr_by_month(h), "\n")
    print("SLA attainment by priority\n", sla_attainment(h), "\n")
    print("Category Pareto\n", category_pareto(h), "\n")
    o = load_open_set()
    print(f"Backlog aging ({len(o)} open tickets as of {o['opened_at'].max()})\n", backlog_aging(o))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
