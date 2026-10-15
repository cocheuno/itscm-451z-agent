"""Routing: which assignment group works a category (Rung 3; the A2 routing metric, folded into Module 8).

The simplest routing model there is: for each category, the group that handled most of its closed
incidents in the history. A lookup table, learned from data, with no parameters to tune. On this corpus
every category maps to exactly one group (the crosstab is diagonal), so the table is also perfect on the
holdout set; a real desk has overlap, and the table's accuracy is what the harness's routing_accuracy
measures. The agent proposes the group through assign_incident; a human approves.
"""
from __future__ import annotations

import pandas as pd

# Measured from data/eval/incidents_history.csv by routing_table(); the test checks they still agree.
ROUTES = {
    "Database": "Database Admin",
    "Hardware": "Desktop Support",
    "Inquiry / Help": "Service Desk L1",
    "Network": "Network Ops",
    "Security": "Security Ops",
    "Software": "Application Support",
}


def routing_table(history: pd.DataFrame) -> dict[str, str]:
    """Majority assignment group per category: for each category, the group with the most closed incidents."""
    counts = history.groupby(["category", "assignment_group"]).size()
    return {cat: counts[cat].idxmax() for cat in counts.index.get_level_values(0).unique()}


def route(category: str | None, routes: dict[str, str] = ROUTES) -> str | None:
    """The group for a category, or None when the category is unknown (the agent then proposes nothing)."""
    if category is None:
        return None
    return routes.get(category)
