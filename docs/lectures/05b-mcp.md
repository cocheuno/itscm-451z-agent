# Module 5, session 2: the Model Context Protocol

Before this lecture: session 1 is committed on your `module-05` branch and your PDI has the groups, items
and articles loaded. About 50 minutes of guided work. Commands are for Windows; a **Mac:** box follows
where a command differs.

## What you will be able to do afterwards

1. Explain what MCP is, what problem it solves, and what a server, a client and a transport are.
2. Run the program's read tools as an MCP server, connect a client to it, and watch a call go through the
   registry.
3. Say why the server exposes exactly the read-tier tools and what would happen if it exposed more.
4. Connect a real AI client (Claude Code or Claude Desktop) to your server and ask it a question about
   your PDI.

## Where the repository already stands

| Item | On `main`? | What you do |
|---|---|---|
| The server, `src\agent\mcp_server.py` | Yes | Read it (Part 1) |
| The scripted client, `scripts\mcp_client_check.py` | Yes | Run and read it (Part 2) |
| Audit entries for MCP calls | No | Wire them (Part 2, Step 3) |

## Why this session exists

**The problem MCP solves.** The tools from session 1 are Python functions. Only Python in this repository
can call them. An AI model that lives somewhere else (a chat assistant on your laptop, a colleague's
program) cannot. Every vendor used to invent its own way of describing tools to a model; the Model Context
Protocol is the open standard that replaced that. One conversation in which a **server** says "here are my
tools and their schemas" and a **client** says "call this one with these arguments". Your three tools,
described once in their schema files, become usable by any MCP client without changing them.

**The capability ladder.** Rung 2 is a read-only program. MCP is how its read-only surface is offered to
the outside without giving anything else away: the server is built from the registry and skips every
schema whose tier is not `read`. The tier file is still the only place a permission lives.

**Analytics.** No model today. But A2's health report (Module 6) is narrated by an LLM that calls the KPI
tools, and those tools will be registered and exposed the same way as today's three. What you learn about
schemas and servers today is what makes A2's numbers traceable.

## Words you need

- **MCP:** Model Context Protocol. A standard by which a model-facing program discovers and calls tools.
- **Server:** the program that owns the tools. Yours is `agent.mcp_server`.
- **Client:** the program that wants to call them: Claude Desktop, Claude Code, or a script.
- **Transport:** how the two talk. **stdio** means the client starts the server as a child process and
  they exchange lines of text through its standard input and output. No network, no port, no key. That is
  what you use today.
- **JSON-RPC:** the message format underneath, a request with an id and a reply with the same id. You
  never write it by hand; the `mcp` library does.
- **Initialize:** the handshake at the start of every session where both sides state their versions and
  what they can do.

## Before you start

```
git status
python -c "import mcp; print('mcp ok')"
python -m pytest tests\test_readonly_tools.py -q
```

Expected: nothing to commit; `mcp ok`; six passed. If the import fails,
`python -m pip install -r requirements.txt`.

## Part 1: how the server is built (10 min)

Open `src\agent\mcp_server.py`. It is short. Read it with these notes:

- `MCPServer(name)` from the `mcp` library creates a server object.
- `build_server(registry)` loops over the registry's tools and **skips every one whose tier is not
  `read`**. That loop is the security boundary of the server.
- For each read tool, `_register` defines a small Python function whose parameters match the schema
  (`lookup_ci(name)`, `search_kb(query, limit=5)`, `find_similar_incidents(text, limit=5)`) and marks it
  with `@server.tool(name=..., description=...)`. The library reads the parameter names and types and
  builds the MCP input schema from them; the description comes from the schema file, so the model reads
  the same text it would read inside the program. `classify_incident` is read-tier too, but `_register`
  has no closure for it, so the server does not offer it: it is for the program's own loop, not for
  outside clients.
- Each function's body is one line: `registry.dispatch(...)`. The server never calls a tool function
  directly. Tiers, and from today the audit entry, apply to MCP calls exactly as to internal ones.
- `main()` builds a registry, attaches the tools to a live ServiceNow client, and runs the server over
  stdio.

## Part 2: run it and talk to it (15 min)

### Step 1: the scripted client

`scripts\mcp_client_check.py` is an MCP client in forty lines. It starts your server as a child process,
performs the handshake, lists the tools, and optionally calls one.

```
python scripts\mcp_client_check.py
```

Expected:

```
tools exposed by agent.mcp_server:
  find_similar_incidents   Find recently resolved incidents whose short description is similar to the cu
  lookup_ci                Look up a configuration item in the CMDB by exact name. Returns class, support
  search_kb                Search published knowledge-base articles for text relevant to an incident. Re
```

Three tools, no `assign_incident`, no `classify_incident`. Now call one:

```
python scripts\mcp_client_check.py --call lookup_ci name=VPN-GW-01
python scripts\mcp_client_check.py --call search_kb query="vpn drops from home" limit=2
```

Expected: the same dictionaries you saw in Python in session 1, printed as JSON. What happened
underneath: the client wrote a `tools/call` message to the server's standard input; the server called
`registry.dispatch`, which called `lookup_ci`, which called your PDI; the result came back as JSON on
standard output.

If the client hangs: the server failed to start, usually because `.env` cannot be found. Run
`python -m agent.mcp_server` by itself; it should sit silently waiting for input (Ctrl+C to stop). Any
error it prints is the cause.

### Step 2: read the client

Open `scripts\mcp_client_check.py`. Four lines matter:

- `StdioServerParameters(command=sys.executable, args=["-m", "agent.mcp_server"], cwd=...)`: how to
  start the server. Any MCP client, including Claude Desktop, is configured with exactly this: a command,
  its arguments, and a working folder.
- `stdio_client(params)`: starts the process and gives back a read stream and a write stream.
- `ClientSession(read, write)` then `await session.initialize()`: the handshake.
- `await session.list_tools()` and `await session.call_tool(name, args)`: the two operations the course
  uses.

### Step 3: make MCP calls audited

The server's `main()` builds the registry but does not pass an audit log to `dispatch`, so MCP calls leave
no trace yet. Two edits in `src\agent\mcp_server.py`:

1. Near the top, after the existing imports, add:

   ```python
   from agent.audit import AuditLog

   AUDIT = AuditLog()
   ```

2. In `_register`, each of the three one-line bodies reads `return registry.dispatch("...", {...})`. Add
   `, audit=AUDIT` inside the parentheses of each, so for example:

   ```python
           return registry.dispatch("lookup_ci", {"name": name}, audit=AUDIT)
   ```

Then:

```
python scripts\mcp_client_check.py --call lookup_ci name=IDP-01
python -m pytest tests\test_readonly_tools.py -q
```

Expected: the call prints as before, the last line of `logs\audit.jsonl` is a `lookup_ci` entry, and the
tests pass.

## Part 3: connect a real client (15 min)

Pick whichever you have installed.

**Claude Code** (terminal). From the clone folder:

```
claude mcp add itscm451z -- python -m agent.mcp_server
claude
```

Then ask: "Use the itscm451z tools to look up VPN-GW-01 and find a knowledge article about VPN drops."
Claude Code lists the three tools when it starts and asks before calling each one; approve, and read the
answer against what the scripted client returned.

**Claude Desktop.** Open Settings, Developer, Edit Config, and add inside `mcpServers`:

```json
"itscm451z": {
  "command": "C:\\full\\path\\to\\your\\clone\\.venv\\Scripts\\python.exe",
  "args": ["-m", "agent.mcp_server"]
}
```

> **Mac:** the command is the full path to `.venv/bin/python` inside your clone.

This works from any folder because the install step made the `agent` package importable everywhere and
the server reads `.env` from the repository, not from the current folder. Restart Claude Desktop; the
tools icon shows three tools. Ask the same question.

Two things to observe and write down:

1. The model chose which tool to call and with what arguments. You did not tell it the tool names. That
   is the description field doing its work.
2. The answer contains an IP address if the model chose to repeat it. Nothing today stops that; the
   Module 12 output filter is where `SENSITIVE_CI_FIELDS` is enforced, and the governance rule already
   says such data never reaches a customer. This is a live example of why the rule sits at the output.

## Part 4: what the server does not do (5 min)

```
python scripts\mcp_client_check.py --call assign_incident sys_id=x assignment_group=y rationale=z
```

Expected: an error from the server that no such tool exists. It is not hidden; it was never registered,
because its tier is not `read`. When Rung 3 adds write tools they will still not appear here: an MCP
server for the outside world stays read-only, and the write path goes through approvals inside the
program.

## Deliverable

1. Create `docs\journal\module-05b.md`:

   ```markdown
   # Module 5, session 2: MCP

   ## One call through the scripted client
   <paste the output of one --call>

   ## The real client
   <which client; what it did with the tools; whether it repeated sensitive fields>

   ## Help I used
   <one or two lines>
   ```

2. Save the snapshot:

   ```
   git status
   git add src\agent\mcp_server.py docs\journal\module-05b.md
   git status
   git commit -m "Rung 2: MCP server audits every call"
   git log --oneline -3
   ```

   > **Mac:** forward slashes in the `git add` line.

## What is next

Module 6: the program's loop. The model receives a ticket and the tool schemas, decides which to call,
calls them through the registry, and writes a triage note; the KPI tools (MTTR, SLA attainment by
priority, backlog aging, category Pareto) join the registry; sentence embeddings replace keyword matching
in the two retrieval tools; and the Service Desk Health Report is narrated from audited numbers. A2 is due
Oct 8.

## Check yourself

1. Where does the MCP server get its tool descriptions, and why does that matter? (From the schema files;
   the model sees the same text inside the program and outside it.)
2. What is the transport in today's setup, and what does it mean that no key was needed? (stdio; the
   client starts the server as a child process on your own machine, so the only secret is your `.env`,
   which the server reads itself.)
3. A colleague adds a fourth schema at tier `propose` and restarts the server. How many tools does the
   client see? (Three. The loop skips anything that is not `read`.)
4. What single file change would make the client see it, and what else must accompany that change? (The
   `action_tier` field; an ADR and a governance row.)
