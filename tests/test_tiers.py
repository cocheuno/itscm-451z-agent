"""Tier enforcement must not be bypassable by anything a model says. Extended in Modules 8 and 12."""
from agent.tools.registry import Registry
from agent.tools.tiers import Tier


def test_all_schemas_declare_a_tier():
    r = Registry()
    assert r.tools, "no schemas found"
    for spec in r.tools.values():
        assert isinstance(spec.tier, Tier)


def test_read_tools_cannot_write():
    r = Registry()
    for name in ("search_kb", "lookup_ci", "find_similar_incidents"):
        assert r.tools[name].tier is Tier.READ
        assert not r.tools[name].tier.writes


def test_write_tools_declare_write_tiers_and_the_mcp_server_hides_them():
    from agent.mcp_server import build_server

    r = Registry()
    assert r.tools["assign_incident"].tier is Tier.EXECUTE_WITH_APPROVAL
    assert r.tools["resolve_incident"].tier is Tier.EXECUTE_WITH_APPROVAL
    assert r.tools["add_comment"].tier is Tier.PROPOSE
    assert not Tier.PROPOSE.writes and Tier.EXECUTE_WITH_APPROVAL.needs_approval
    server = build_server(r)
    if hasattr(server, "_tool_manager"):
        assert {t.name for t in server._tool_manager.list_tools()} == {"lookup_ci", "search_kb", "find_similar_incidents"}
