"""Match a new incident to a published known-error article.

The article is found by its source problem and its CI. Text similarity is a
second check. The threshold below was chosen from the fixture texts before
any live result was read.
"""

from __future__ import annotations

import html
import math
import re

# Cosine of term counts. 0.20 sat under the printer decoy, so the bar is the
# midpoint of the E01 fixture pair and that decoy. Do not retune from a live run.
_E01 = (
    "Shoppers see a timeout when the application cannot write because there is no rotation of logs "
    "Larkspur Outfitters incident. Log rotation stopped. The log directory filled."
)
_ARTICLE = (
    "E2E- Known error for syn-store-cdn "
    "Log rotation stopped. The log directory filled. "
    "Retry the page. Clear the filled log files at the next maintenance window."
)
_DECOY = "A jammed printer queue held the lane receipt and the lead asked for paper"
MARKER = "E2E-"
_TOKEN = re.compile(r"[a-z0-9]+")
_TAG = re.compile(r"<[^>]+>")


def _plain(text: str) -> str:
    """Drop markup so a stored article is scored on the same words as the fixture."""
    return html.unescape(_TAG.sub(" ", text))


def _counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in _TOKEN.findall(text.lower()):
        counts[token] = counts.get(token, 0) + 1
    return counts


def similarity(left: str, right: str) -> float:
    """Cosine similarity of the two texts' term counts. Empty text scores 0."""
    first = _counts(left)
    second = _counts(right)
    if not first or not second:
        return 0.0
    keys = set(first) | set(second)
    dot = sum(first.get(key, 0) * second.get(key, 0) for key in keys)
    left_norm = math.sqrt(sum(value * value for value in first.values()))
    right_norm = math.sqrt(sum(value * value for value in second.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


# Fixed from the two fixture strings above, before any live tick.
SIMILARITY_MIN = (similarity(_E01, _ARTICLE) + similarity(_DECOY, _ARTICLE)) / 2


def match_known_error(
    incident: dict,
    articles: list[dict],
    problems: dict[str, dict],
    *,
    minimum: float = SIMILARITY_MIN,
) -> dict | None:
    """The best article for this incident, or None.

    `incident` carries cmdb_ci, short_description, and description.
    Each article carries number, short_description, text, source, cmdb_ci,
    and workflow_state. `problems` is keyed by the problem sys_id and carries
    number, known_error, and workaround.
    """
    incident_text = f"{incident.get('short_description', '')} {incident.get('description', '')}"
    ci = str(incident.get("cmdb_ci") or "")
    best: tuple[float, str, dict] | None = None
    for article in articles:
        if str(article.get("workflow_state") or "") != "published":
            continue
        short = str(article.get("short_description") or "")
        if not short.startswith(MARKER):
            continue
        if str(article.get("cmdb_ci") or "") != ci:
            continue
        problem = problems.get(str(article.get("source") or ""))
        if problem is None or not _truthy(problem.get("known_error")):
            continue
        workaround = str(problem.get("workaround") or "")
        if not workaround:
            continue
        article_text = _plain(f"{short} {article.get('text', '')}")
        score = similarity(_plain(incident_text), article_text)
        if score < minimum:
            continue
        number = str(article.get("number") or "")
        if best is None or score > best[0] or (score == best[0] and number < best[1]):
            best = (score, number, {"article": article, "problem": problem, "score": score})
    if best is None:
        return None
    return best[2]


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "t", "yes"}
