"""Diagnostic analytics (A3, Module 8): did a change cause incidents?

Descriptive analytics says what happened (the KPIs). Diagnostic analytics asks why. The question here is
the one every change manager asks after a maintenance window: did ticket volume go up afterwards, and by
how much more than it would have anyway?

The method is a comparison of two counts per change record:

- **observed**: incidents opened in the window after the change finished (default: the 72 hours after
  `end`, because the seeded failures surface in the first one to three days).
- **expected**: how many that same window would normally hold, estimated from the 28 days before the
  change (the baseline): tickets per hour over the baseline, times the window's hours.

Their ratio is the lift. A ratio near 1 means nothing happened; a ratio of 2.5 means the window held two
and a half times its usual volume. Two refinements keep the ratio honest. The same comparison is made per
category, because a change to a switch should show up in Network and nowhere else, and a lift confined to
one category is far more believable than a lift spread evenly. And **surprise** asks how often the
baseline itself produced a window this busy: slide a window of the same length across the baseline one
day at a time and count the share that held at least `observed` tickets. A surprise of 0.0 means no
baseline window came close; 0.3 means it happens almost a third of the time, so the lift is noise.

    python -m agent.analytics.change_impact                 # the table, one row per change
    python -m agent.analytics.change_impact --plot          # also eval/reports/change_impact.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from agent.analytics.features import ROOT, load_history

CHANGES = ROOT / "data" / "eval" / "changes.csv"
WINDOW_HOURS = 72
BASELINE_DAYS = 28


def load_changes(path: Path = CHANGES) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["start", "end"])


def incidents_in_window(history: pd.DataFrame, start: pd.Timestamp, hours: int = WINDOW_HOURS,
                        category: str | None = None) -> pd.DataFrame:
    """Rows opened at or after `start` and before `start + hours`, optionally one category only."""
    end = start + pd.Timedelta(hours=hours)
    rows = history[(history["opened_at"] >= start) & (history["opened_at"] < end)]
    if category is not None:
        rows = rows[rows["category"] == category]
    return rows


def observed_count(history: pd.DataFrame, change_end: pd.Timestamp, hours: int = WINDOW_HOURS,
                   category: str | None = None) -> int:
    return len(incidents_in_window(history, change_end, hours, category))


def expected_count(history: pd.DataFrame, change_end: pd.Timestamp, hours: int = WINDOW_HOURS,
                   baseline_days: int = BASELINE_DAYS, category: str | None = None) -> float:
    """TODO(student, Module 8 session 1): the number of incidents a window of `hours` would normally hold.

    Take the rows opened in the `baseline_days` days before `change_end` (and in `category`, when given),
    work out tickets per hour over that baseline, and multiply by `hours`. Exact code in lecture 08a.
    """
    raise NotImplementedError


def surprise(history: pd.DataFrame, change_end: pd.Timestamp, observed: int, hours: int = WINDOW_HOURS,
             baseline_days: int = BASELINE_DAYS, category: str | None = None) -> float:
    """Share of same-length windows in the baseline, one per day, that held at least `observed` incidents."""
    starts = [change_end - pd.Timedelta(days=d) for d in range(baseline_days, 0, -1)
              if change_end - pd.Timedelta(days=d) + pd.Timedelta(hours=hours) <= change_end]
    if not starts:
        return float("nan")
    busy = sum(observed_count(history, s, hours, category) >= observed for s in starts)
    return round(busy / len(starts), 3)


def impact_table(history: pd.DataFrame, changes: pd.DataFrame, hours: int = WINDOW_HOURS,
                 baseline_days: int = BASELINE_DAYS) -> pd.DataFrame:
    """One row per change: observed, expected, ratio and surprise over all categories, then the same for the
    category with the largest lift. Sorted by ratio, largest first."""
    rows = []
    for ch in changes.itertuples(index=False):
        obs = observed_count(history, ch.end, hours)
        exp = expected_count(history, ch.end, hours, baseline_days)
        best = None
        for cat in sorted(history["category"].unique()):
            o = observed_count(history, ch.end, hours, cat)
            e = expected_count(history, ch.end, hours, baseline_days, cat)
            r = o / e if e else float("nan")
            if best is None or r > best[3]:
                best = (cat, o, e, r)
        rows.append({"number": ch.number, "cmdb_ci": ch.cmdb_ci, "end": ch.end, "observed": obs,
                     "expected": round(exp, 1), "ratio": round(obs / exp, 2) if exp else float("nan"),
                     "surprise": surprise(history, ch.end, obs, hours, baseline_days),
                     "top_category": best[0], "top_observed": best[1], "top_expected": round(best[2], 1),
                     "top_ratio": round(best[3], 2),
                     "top_surprise": surprise(history, ch.end, best[1], hours, baseline_days, best[0])})
    return pd.DataFrame(rows).sort_values("ratio", ascending=False).reset_index(drop=True)


def plot(history: pd.DataFrame, changes: pd.DataFrame, table: pd.DataFrame, out: Path,
         hours: int = WINDOW_HOURS) -> Path:
    """Daily volume with every change marked and the window after the largest-lift change shaded."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    daily = history.groupby(history["opened_at"].dt.floor("D")).size()
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(daily.index, daily.values, lw=1)
    for ch in changes.itertuples(index=False):
        ax.axvline(ch.end, color="grey", ls=":", lw=1)
        ax.text(ch.end, daily.max(), ch.number, rotation=90, va="top", ha="right", fontsize=7)
    top = table.iloc[0]
    ax.axvspan(top["end"], top["end"] + pd.Timedelta(hours=hours), alpha=0.2)
    ax.set_title(f"Incidents opened per day; dotted: change ends; shaded: {hours} h after {top['number']} "
                 f"(ratio {top['ratio']})")
    ax.set_ylabel("tickets")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=120)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=WINDOW_HOURS, help="window after each change's end")
    ap.add_argument("--baseline-days", type=int, default=BASELINE_DAYS)
    ap.add_argument("--plot", action="store_true", help="write eval/reports/change_impact.png")
    a = ap.parse_args(argv)
    pd.set_option("display.width", 160)
    h, c = load_history(), load_changes()
    t = impact_table(h, c, a.hours, a.baseline_days)
    print(f"{len(c)} changes; window {a.hours} h after end; baseline {a.baseline_days} days before\n")
    print(t.to_string(index=False))
    top = t.iloc[0]
    print(f"\nlargest lift: {top['number']} ({top['cmdb_ci']}), {top['observed']} observed vs {top['expected']} "
          f"expected, ratio {top['ratio']}; {top['top_category']} alone {top['top_observed']} vs "
          f"{top['top_expected']}, ratio {top['top_ratio']}")
    if a.plot:
        print("plot:", plot(h, c, t, ROOT / "eval" / "reports" / "change_impact.png", a.hours))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
