"""Category, priority, and assignment for one incident.

Category comes from a caller-supplied table keyed by CI class. The committed
category model is not called. Priority uses the impact and urgency matrix,
except the pair this PDI's data lookup stores as 4.
"""

from __future__ import annotations

from agent.workflow.sla import priority

# dl_u_priority on this PDI. The course matrix maps the same pair to 5.
PDI_PRIORITY = {(3, 3): 4}


def category_for_class(ci_class: str, table: dict[str, str]) -> str:
    """Return the category for a CI class, or empty when the class is unknown."""
    return table.get(ci_class, "")


def priority_on_this_pdi(impact: int, urgency: int) -> int:
    """The priority this PDI stores for the impact and urgency."""
    override = PDI_PRIORITY.get((impact, urgency))
    if override is not None:
        return override
    return priority(impact, urgency)
