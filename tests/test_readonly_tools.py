"""Module 5 read-tier tools against a fake client; the MCP server exposes exactly the read tools."""
from __future__ import annotations

import asyncio
import json
import re

import pytest

from agent.tools import readonly
from agent.tools.registry import Registry

KB_ROWS = [
    {"number": "KB0010001", "short_description": "[SYN] VPN disconnects or will not connect from home",
     "text": "<p>Symptoms: the VPN client connects and drops. Checks: client version, clock.</p>",
     "workflow_state": "published"},
    {"number": "KB0010007", "short_description": "[SYN] Print jobs stuck in the queue or spooler errors",
     "text": "<p>Restart the Print Spooler service; PRINT-SRV-02 queue.</p>", "workflow_state": "published"},
]
INC_ROWS = [
    {"number": "INC0010300", "short_description": "[SYN] VPN drops every hour since Friday", "category": "network",
     "subcategory": "VPN", "assignment_group": "", "close_notes": "Renewed gateway certificate.", "correlation_id": "SYN1"},
    {"number": "INC0010301", "short_description": "[SYN] Printer jams again", "category": "hardware",
     "subcategory": "Printer", "assignment_group": "", "close_notes": "Cleared jam.", "correlation_id": "SYN2"},
]
CI_ROW = {"sys_id": "abc", "name": "VPN-GW-01", "sys_class_name": "cmdb_ci_netgear", "support_group": "Network Ops",
          "owned_by": "", "ip_address": "10.20.0.1", "operational_status": "1"}


class FakeSN:
    """Answers LIKE queries the way the Table API would: any term after LIKE matching the row text."""

    def __init__(self):
        self.calls = []

    def list(self, table, query="", fields=None, limit=100, offset=0):
        self.calls.append((table, query))
        terms = re.findall(r"LIKE([a-z0-9\-]+)", query)
        if table == "cmdb_ci":
            return [CI_ROW] if "name=VPN-GW-01" in query else []
        if table == "kb_knowledge":
            return [r for r in KB_ROWS if any(t in (r["short_description"] + r["text"]).lower() for t in terms)]
        if table == "incident":
            return [r for r in INC_ROWS if any(t in r["short_description"].lower() for t in terms)]
        return []


def test_keywords_drop_stopwords_and_prefer_long_words():
    assert readonly.keywords("The VPN drops at home again") == ["drops", "home", "vpn"]
    assert readonly.keywords("hi team") == []


def test_lookup_ci_found_and_not_found():
    sn = FakeSN()
    hit = readonly.lookup_ci(sn, "VPN-GW-01")
    assert hit["found"] and hit["sys_class_name"] == "cmdb_ci_netgear" and hit["ip_address"] == "10.20.0.1"
    assert readonly.lookup_ci(sn, "NOPE") == {"found": False, "name": "NOPE"}
    assert sn.calls[0] == ("cmdb_ci", "name=VPN-GW-01")


def test_search_kb_ranks_by_keyword_hits_and_excerpts_plain_text():
    out = readonly.search_kb(FakeSN(), "vpn client drops", limit=5)
    assert out and out[0]["number"] == "KB0010001" and "<p>" not in out[0]["excerpt"]
    assert readonly.search_kb(FakeSN(), "the a an") == []


def test_find_similar_incidents_returns_resolved_matches_with_close_notes():
    sn = FakeSN()
    out = readonly.find_similar_incidents(sn, "VPN keeps dropping", limit=3)
    assert out[0]["number"] == "INC0010300" and out[0]["close_notes"].startswith("Renewed")
    assert sn.calls[0][1].startswith("state=7^")


def test_bind_all_dispatches_through_the_registry_at_read_tier():
    r = Registry()
    readonly.bind_all(r, FakeSN())
    assert r.dispatch("lookup_ci", {"name": "VPN-GW-01"})["found"]
    assert r.dispatch("search_kb", {"query": "printer spooler"})[0]["number"] == "KB0010007"
    with pytest.raises((RuntimeError, NotImplementedError)):  # a write tool is unreachable: unbound, and above read tier
        r.dispatch("assign_incident", {"sys_id": "x", "assignment_group": "g", "rationale": "r"})


def test_mcp_server_exposes_only_read_tools_and_calls_through_the_registry():
    pytest.importorskip("mcp")
    from agent.mcp_server import build_server

    r = Registry()
    readonly.bind_all(r, FakeSN())
    server = build_server(r)
    tools = asyncio.run(server.list_tools())
    assert sorted(t.name for t in tools) == ["find_similar_incidents", "lookup_ci", "search_kb"]
    assert "assign_incident" not in {t.name for t in tools}
    schema = next(t for t in tools if t.name == "search_kb").input_schema
    assert schema["required"] == ["query"] and "limit" in schema["properties"]
    result = asyncio.run(server.call_tool("lookup_ci", {"name": "VPN-GW-01"}))
    assert not result.is_error
    payload = result.structured_content or json.loads(result.content[0].text)
    assert payload["found"] is True and payload["name"] == "VPN-GW-01"
