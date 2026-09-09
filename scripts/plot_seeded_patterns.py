"""Instructor eyeball check of the seeded patterns in the historical corpus.

Reads the committed corpus (data/eval/) and draws four panels: daily volume with the change records
marked, weekday x hour volume heatmap, monthly mean time-to-resolve by category, and SLA breach rate by
priority split by business/off hours. Pass --manifest to also shade the cluster windows.

    python scripts/plot_seeded_patterns.py                                  # -> eval/reports/seeded_patterns.png
    python scripts/plot_seeded_patterns.py --manifest ~/.itscm451z/seeded_truth_manifest.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "eval"
OUT = ROOT / "eval" / "reports" / "seeded_patterns.png"
# Fixed categorical order (never cycled): taxonomy order -> palette slots.
CATEGORY_ORDER = ["Network", "Hardware", "Software", "Database", "Inquiry / Help", "Security"]
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def style(ax: plt.Axes, title: str) -> None:
    ax.set_title(title, loc="left", fontsize=11, color=INK, pad=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def load(corpus_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    inc = pd.read_csv(corpus_dir / "incidents_history.csv", parse_dates=["opened_at", "resolved_at", "closed_at"])
    chg = pd.read_csv(corpus_dir / "changes.csv", parse_dates=["start", "end"])
    inc["breached"] = inc["made_sla"].astype(str).str.lower() == "false"
    inc["off_hours"] = (inc["opened_at"].dt.weekday >= 5) | ~inc["opened_at"].dt.hour.between(7, 17)
    return inc, chg


def panel_volume(ax: plt.Axes, inc: pd.DataFrame, chg: pd.DataFrame, manifest: dict | None) -> None:
    daily = inc.set_index("opened_at").resample("D").size()
    ax.plot(daily.index, daily.values, color=PALETTE[0], linewidth=0.8, alpha=0.35, label="daily")
    ax.plot(daily.index, daily.rolling(7, center=True).mean().values, color=PALETTE[0], linewidth=2, label="7-day mean")
    for _, c in chg.iterrows():
        ax.axvline(c["end"], color=MUTED, linewidth=0.8, linestyle=":", alpha=0.6)
    top = float(daily.max())
    if manifest:
        lo, hi = (pd.Timestamp(s) for s in manifest["change_spike"]["window"])
        ax.axvspan(lo, hi, color=PALETTE[1], alpha=0.18, label=f"{manifest['change_spike']['change']['number']} +24-72h")
        # cluster windows as a rug below the axis so they never collide with the data or the legend
        for i, cl in enumerate(manifest["clusters"]):
            a, b = (pd.Timestamp(w) for w in cl["window"])
            y = -top * (0.06 + 0.05 * i)
            ax.hlines(y, a, b, color=PALETTE[2], linewidth=2, alpha=0.8)
            ax.text(a, y, cl["id"] + " ", fontsize=7, color=MUTED, va="center", ha="right")
        ax.set_ylim(-top * (0.06 + 0.05 * len(manifest["clusters"])), top * 1.45)
    else:
        ax.set_ylim(0, top * 1.45)
    ax.set_ylabel("incidents opened / day", color=MUTED, fontsize=9)
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=3)
    style(ax, "Volume over time (dotted: change records; expect Monday peaks and an upward drift)")


def panel_heatmap(ax: plt.Axes, inc: pd.DataFrame, fig: plt.Figure) -> None:
    grid = pd.crosstab(inc["opened_at"].dt.weekday, inc["opened_at"].dt.hour).reindex(range(7), fill_value=0)
    grid = grid.reindex(columns=range(24), fill_value=0)
    im = ax.imshow(grid.values, aspect="auto", cmap="Blues", interpolation="nearest")
    ax.set_yticks(range(7), DOW)
    ax.set_xticks(range(0, 24, 3), [f"{h:02d}" for h in range(0, 24, 3)])
    ax.set_xlabel("hour opened", color=MUTED, fontsize=9)
    ax.yaxis.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02).set_label("incidents", color=MUTED, fontsize=8)
    style(ax, "Weekday x hour volume (expect Monday 08-12 hot spot, quiet weekends)")
    ax.yaxis.grid(False)


def panel_mttr(ax: plt.Axes, inc: pd.DataFrame) -> None:
    monthly = inc.assign(month=inc["opened_at"].dt.to_period("M").dt.to_timestamp(), hours=inc["resolve_minutes"] / 60)
    table = monthly.pivot_table(index="month", columns="category", values="hours", aggfunc="mean")
    span = float(table.max().max() - table.min().min())
    ends = sorted(float(table[c].iloc[-1]) for c in CATEGORY_ORDER if c in table)
    for cat, color in zip(CATEGORY_ORDER, PALETTE, strict=True):
        if cat not in table:
            continue
        s = table[cat]
        ax.plot(s.index, s.values, color=color, linewidth=2, marker="o", markersize=4, label=cat)
        end = float(s.iloc[-1])
        crowded = any(0 < abs(end - other) < 0.05 * span for other in ends)
        if not crowded:  # selective direct labels: only where they cannot collide; the legend carries the rest
            ax.text(s.index[-1] + pd.Timedelta(days=4), end, cat, fontsize=7, color=MUTED, va="center")
    ax.set_ylabel("mean hours to resolve", color=MUTED, fontsize=9)
    ax.legend(fontsize=8, frameon=False, ncol=2)
    style(ax, "Monthly MTTR by category (expect one category climbing month over month)")


def panel_breach(ax: plt.Axes, inc: pd.DataFrame) -> None:
    rate = inc.groupby(["priority", "off_hours"])["breached"].mean().unstack("off_hours").reindex(range(1, 6))
    width = 0.38
    for k, (label, color) in enumerate(((False, PALETTE[0]), (True, PALETTE[1]))):
        vals = rate[label].fillna(0).values
        xs = [p - width / 2 + k * width for p in range(1, 6)]
        ax.bar(xs, vals, width=width - 0.04, color=color, label="business hours" if not label else "off hours")
        for x, v in zip(xs, vals, strict=True):
            ax.text(x, v + 0.01, f"{v:.0%}", ha="center", fontsize=7, color=MUTED)
    ax.set_xticks(range(1, 6), [f"P{p}" for p in range(1, 6)])
    ax.set_ylabel("SLA breach rate", color=MUTED, fontsize=9)
    ax.set_ylim(0, min(1.0, rate.max().max() + 0.15))
    ax.legend(fontsize=8, frameon=False)
    style(ax, "Breach rate by priority and time of day (expect a gradient, not a step function)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus-dir", type=Path, default=CORPUS)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--manifest", type=Path, default=None, help="instructor-only manifest to overlay seeded windows")
    a = ap.parse_args()
    inc, chg = load(a.corpus_dir)
    manifest = json.loads(a.manifest.expanduser().read_text()) if a.manifest else None

    fig, axes = plt.subplots(2, 2, figsize=(15, 10), facecolor="#fcfcfb")
    fig.suptitle(f"Seeded patterns: {len(inc)} closed incidents, {inc['opened_at'].min():%Y-%m-%d} to "
                 f"{inc['opened_at'].max():%Y-%m-%d}", x=0.02, ha="left", fontsize=13, color=INK)
    panel_volume(axes[0][0], inc, chg, manifest)
    panel_heatmap(axes[0][1], inc, fig)
    panel_mttr(axes[1][0], inc)
    panel_breach(axes[1][1], inc)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=130)
    print(f"wrote {a.out}")
    summary = inc.groupby(inc["opened_at"].dt.to_period("M"))["resolve_minutes"].mean().round().to_dict()
    print("monthly mean resolve minutes (all categories):", {str(k): int(v) for k, v in summary.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
