"""Feature helpers shared by training, prediction and the notebooks.

The authoritative history is data/eval/incidents_history.csv. The PDI copy has no usable timestamps
(ADR-0002), so anything time-based reads the CSV and joins the PDI on correlation_id when it needs sys_ids.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HISTORY = ROOT / "data" / "eval" / "incidents_history.csv"
DATE_COLS = ["opened_at", "resolved_at", "closed_at"]
TEXT_COLS = ("short_description", "description")
TARGET = "category"
DEFAULT_CUTOFF = "2026-08-01"  # train on March..July, test on August (ADR-0003)


def load_history(path: Path = HISTORY) -> pd.DataFrame:
    """The closed-incident corpus with parsed timestamps and a boolean made_sla."""
    df = pd.read_csv(path, parse_dates=DATE_COLS)
    df["made_sla"] = df["made_sla"].astype(str).str.lower().eq("true")
    return df


def text_of(row: Mapping) -> str:
    """The text a classifier sees: short description plus description, missing pieces tolerated."""
    return " ".join(str(row.get(c) or "") for c in TEXT_COLS).strip()


def time_split(df: pd.DataFrame, cutoff: str = DEFAULT_CUTOFF, col: str = "opened_at") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on rows opened before `cutoff`, test on rows opened at or after it.

    A random split would leak: paraphrases of the same seeded incident family land on both sides, and the
    August test month is also where the distribution has drifted (trend, degrading Hardware). Time order is
    the honest split for a model that will score tickets arriving after it was trained.
    """
    when = pd.Timestamp(cutoff)
    train = df[df[col] < when]
    test = df[df[col] >= when]
    if train.empty or test.empty:
        raise ValueError(f"cutoff {cutoff} leaves train={len(train)} test={len(test)} rows")
    return train, test
