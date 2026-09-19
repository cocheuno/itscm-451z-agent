"""Rung 2, Module 5: the three read-tier tools, implemented against the ServiceNow Table API.

Each function takes exactly the arguments its JSON schema in tools/schemas/ declares and returns plain
dicts and lists (JSON-serialisable), because the same functions are called by the registry, the MCP server,
and, from Module 6, the LLM tool loop. Module 6 (A2) replaces the keyword matching in search_kb and
find_similar_incidents with sentence embeddings; the signatures stay the same.

    from agent.tools.readonly import bind_all
    registry = Registry(); bind_all(registry, ServiceNowClient.from_env())
    registry.dispatch("lookup_ci", {"name": "VPN-GW-01"})
"""
from __future__ import annotations

import re

from agent.servicenow import tables

STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "it", "my", "for", "with", "not",
             "at", "from", "this", "that", "i", "we", "our", "again", "please", "hi", "team", "since"}
KB_FIELDS = ["number", "short_description", "text", "workflow_state"]
SIMILAR_FIELDS = ["number", "short_description", "category", "subcategory", "assignment_group", "close_notes",
                  "correlation_id"]


def keywords(text: str, limit: int = 6) -> list[str]:
    """The distinctive words of a query: lower-case, letters and digits only, stopwords dropped, longest first."""
    words = [w for w in re.findall(r"[a-z0-9][a-z0-9\-]+", text.lower()) if w not in STOPWORDS and len(w) > 2]
    seen: list[str] = []
    for w in sorted(set(words), key=lambda w: (-len(w), words.index(w))):
        seen.append(w)
    return seen[:limit]


def excerpt(html: str, width: int = 240) -> str:
    plain = re.sub(r"<[^>]+>", " ", html or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:width] + ("..." if len(plain) > width else "")


def lookup_ci(sn, name: str) -> dict:
    """Exact-name CMDB lookup. Returns the CI fields, including the sensitive ones, for internal use;
    the Module 12 output filter strips SENSITIVE_CI_FIELDS before anything customer-visible."""
    rows = sn.list(tables.CI, f"name={name}", tables.CI_FIELDS, limit=1)
    if not rows:
        return {"found": False, "name": name}
    row = rows[0]
    return {"found": True, **{k: row.get(k, "") for k in tables.CI_FIELDS}}


def search_kb(sn, query: str, limit: int = 5) -> list[dict]:
    """Keyword search over published knowledge articles: any query keyword in the title or body."""
    words = keywords(query)
    if not words:
        return []
    clauses = "^OR".join(f"short_descriptionLIKE{w}^ORtextLIKE{w}" for w in words)
    rows = sn.list(tables.KB, f"workflow_state=published^{clauses}", KB_FIELDS, limit=max(limit * 4, 20))
    scored = []
    for r in rows:
        hay = f"{r.get('short_description', '')} {r.get('text', '')}".lower()
        score = sum(hay.count(w) for w in words)
        scored.append((score, r))
    scored.sort(key=lambda t: -t[0])
    return [{"number": r.get("number", ""), "title": r.get("short_description", ""),
             "excerpt": excerpt(r.get("text", "")), "score": s} for s, r in scored[:limit]]


def find_similar_incidents(sn, text: str, limit: int = 5) -> list[dict]:
    """Resolved incidents whose short description shares keywords with the text. Keyword version (Module 5);
    Module 6 swaps in embeddings behind the same signature."""
    words = keywords(text)
    if not words:
        return []
    clauses = "^OR".join(f"short_descriptionLIKE{w}" for w in words)
    rows = sn.list(tables.INCIDENT, f"state=7^{clauses}", SIMILAR_FIELDS, limit=max(limit * 4, 20))
    scored = []
    for r in rows:
        hay = r.get("short_description", "").lower()
        score = sum(1 for w in words if w in hay)
        scored.append((score, r))
    scored.sort(key=lambda t: -t[0])
    return [{"number": r.get("number", ""), "short_description": r.get("short_description", ""),
             "category": r.get("category", ""), "assignment_group": r.get("assignment_group", ""),
             "close_notes": r.get("close_notes", ""), "score": s} for s, r in scored[:limit]]


def bind_all(registry, sn) -> None:
    """Bind the three read tools to a ServiceNow client so registry.dispatch can call them."""
    registry.bind("lookup_ci", lambda name: lookup_ci(sn, name))
    registry.bind("search_kb", lambda query, limit=5: search_kb(sn, query, limit))
    registry.bind("find_similar_incidents", lambda text, limit=5: find_similar_incidents(sn, text, limit))
