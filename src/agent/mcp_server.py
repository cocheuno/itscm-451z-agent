"""Expose the agent's read-tier tools over the Model Context Protocol (Module 5).

    python -m agent.mcp_server            # stdio transport; an MCP client (Claude Code, Claude Desktop,
                                          # scripts/mcp_client_check.py) spawns this process and talks JSON-RPC

Every tool call goes through the registry, so tiers are enforced here exactly as they are for the agent's
own loop: a client cannot reach assign_incident through this server because its tier is not read.
"""
from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from agent.tools.readonly import bind_all
from agent.tools.registry import Registry
from agent.tools.tiers import Tier


def build_server(registry: Registry, name: str = "itscm451z-agent") -> MCPServer:
    """An MCP server with one tool per read-tier schema in the registry. Descriptions come from the schemas."""
    server = MCPServer(name)
    for tool_name, spec in registry.tools.items():
        if spec.tier is not Tier.READ:
            continue
        _register(server, registry, tool_name, spec.description)
    return server


def _register(server: MCPServer, registry: Registry, tool_name: str, description: str) -> None:
    # One closure per tool. MCP derives the input schema from the Python signature, so each tool gets
    # an explicit signature matching its JSON schema in tools/schemas/.
    if tool_name == "lookup_ci":
        @server.tool(name=tool_name, description=description)
        def lookup_ci(name: str) -> dict:
            return registry.dispatch("lookup_ci", {"name": name})
    elif tool_name == "search_kb":
        @server.tool(name=tool_name, description=description)
        def search_kb(query: str, limit: int = 5) -> list[dict]:
            return registry.dispatch("search_kb", {"query": query, "limit": limit})
    elif tool_name == "find_similar_incidents":
        @server.tool(name=tool_name, description=description)
        def find_similar_incidents(text: str, limit: int = 5) -> list[dict]:
            return registry.dispatch("find_similar_incidents", {"text": text, "limit": limit})


def main() -> int:
    from agent.servicenow.client import ServiceNowClient

    registry = Registry()
    bind_all(registry, ServiceNowClient.from_env())
    build_server(registry).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
