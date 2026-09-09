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
