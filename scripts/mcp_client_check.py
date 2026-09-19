"""Spawn the agent's MCP server over stdio, list its tools, and call one. Module 5 verification.

    python scripts/mcp_client_check.py
    python scripts/mcp_client_check.py --call lookup_ci name=VPN-GW-01
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def run(call: str | None, kv: list[str]) -> int:
    params = StdioServerParameters(command=sys.executable, args=["-m", "agent.mcp_server"], cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools exposed by agent.mcp_server:")
            for t in tools.tools:
                print(f"  {t.name:24s} {t.description[:80]}")
            if call:
                args = {k: (int(v) if v.isdigit() else v) for k, v in (pair.split("=", 1) for pair in kv)}
                result = await session.call_tool(call, args)
                print(f"\n{call}({args}) ->")
                print(json.dumps(result.structured_content, indent=2) if result.structured_content else
                      "\n".join(c.text for c in result.content if getattr(c, "text", None)))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--call", default=None, help="tool name to call after listing")
    ap.add_argument("kv", nargs="*", help="key=value arguments for --call")
    a = ap.parse_args(argv)
    return asyncio.run(run(a.call, a.kv))


if __name__ == "__main__":
    raise SystemExit(main())
