"""The routing table is learned from the history and agrees with the constant the agent ships with."""
from agent.analytics.features import load_history
from agent.workflow.routing import ROUTES, route, routing_table


def test_routing_table_matches_the_shipped_constant():
    assert routing_table(load_history()) == ROUTES


def test_route_handles_unknown_and_missing_categories():
    assert route("Network") == "Network Ops"
    assert route("Weather") is None and route(None) is None
