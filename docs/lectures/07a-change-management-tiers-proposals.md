# Module 7, session 1: change management, tiers, and proposals

Before this lecture: Module 5 is committed on your `module-05` branch. Module 6 (the agent loop, KPI tools,
embeddings, the health report) is folded into Modules 7 and 8: the KPI functions arrive as code you read
and run in Module 8, and the agent loop moves to Rung 4. There is no `v0.2` tag. Rung 3 begins today.
About 60 minutes of guided work. Commands are for Windows; a **Mac:** box follows where a command differs.
A3 builds on Modules 7 and 8 together, on one branch, `module-07`.

## What you will be able to do afterwards

1. Explain ITIL change management in five sentences and map each of its parts onto the agent: change
   record, approval, change window, rollback plan, post-implementation review.
2. Say what each of the four action tiers lets a tool do, and why the tier is a property of the schema.
3. Make the agent propose a write, approve it as a named person, and watch the program execute only the
   approved call, in dry run.
4. Read the two log files the program keeps and point at the line that proves a write was refused.
5. Decide, and write down in an ADR, which tier `add_comment` deserves.

## Where the repository already stands

| Item | On `main`? | What you do |
|---|---|---|
| `Registry.dispatch` with all four tiers and audit entries | Yes | Read it (Part 2); the read-tier audit you wrote in Module 5 is now part of it |
| The approval queue, `src\agent\approvals.py`, and its command | Yes | Run it (Part 3) |
| The three write tools, `src\agent\tools\writes.py` | Yes | Read and run them in dry run (Part 3) |
| Schemas `add_comment.json`, `resolve_incident.json` | Yes | Read them (Part 2); decide one tier (Part 4) |
| The before-image method in `client.py` and `rollback` in `writes.py` | No, marked `TODO(student)` | Session 2 |
| ADR-0007 (the `add_comment` tier), governance sections 2 and 3 | No | Write them (Part 4) |

## Why this session exists

**ITSM.** Everything before today only read. Rung 3 lets the program change a record: assign an incident
to a group, resolve one, comment on one. In a service desk, changes to production systems are governed by
**change management**: the change is written down before it is made (the **change record**, "RFC"),
someone with the authority approves it (for bigger changes, the **CAB**, the change advisory board), it is
made inside an agreed **change window**, with a **rollback plan** ready, and it is reviewed afterwards.
`data\eval\changes.csv` holds six such records from the desk's history; Module 8 asks what they did to
ticket volume. Today, the agent's own writes are put under the same discipline. Every write it wants to
make is a change record (a **proposal**), a named person approves it, the program keeps the **before-image**
so it can roll back, and the audit log is the post-implementation record.

**The capability ladder.** Rung 3 is "write actions under guardrails: tiers, approvals, audit, rollback".
The guardrails are code you can read: the tier in a schema file, one function (`dispatch`) that every call
passes through, and two append-only logs. Nothing a model says can get past them, because the model never
sees them; it only sees tool names and descriptions.

**Analytics.** Today's number is the one the harness will gate on from Module 8: `harmful_action_count`,
the count of audit entries where the program tried a write it was not entitled to. The threshold is zero.
Today you make it nonzero on purpose, so you know what a harmful entry looks like.

## Words you need

- **Change record:** the written description of a change before it is made. In the agent, a proposal.
- **CAB:** change advisory board, the people who approve changes that are not routine. In the agent, the
  approver named on a proposal.
- **Standard change:** pre-approved because it is routine and low risk (monthly patching). **Normal
  change:** needs approval each time. **Emergency change:** made first, reviewed after. The tiers are the
  agent's version of these three.
- **Before-image:** the values of the fields a write is about to change, read just before it changes them.
  The rollback plan in one dictionary.
- **Tier:** `read` (look), `propose` (draft a change for a human to make), `execute_with_approval` (make the
  change, but only after a named person approves this exact call), `autonomous` (make it; no tool has this
  tier, and granting it needs an ADR).
- **Proposal:** a tool call that has not happened: tool, arguments, reason, and an id.
- **Approval id:** the proposal's id once a person approved it. Handing it to `dispatch` is how the program
  proves it may act.
- **Idempotency key:** a short fingerprint of the tool name and arguments. The same call always gets the
  same key, so an approval can be checked against the arguments and a spent approval cannot be reused.
- **Dry run:** `AGENT_MODE=dry_run` in `.env`. The write tools do every check and return what they would
  change; nothing reaches the PDI. Today is all dry run.
- **Harmful action:** an audit entry with `harmful: true`: a write attempted with a missing, mismatched or
  reused approval, or against a record that does not exist.

## Before you start

```
git checkout main
git pull origin main
python -m pip install -r requirements.txt
python -m pytest -q
git checkout -b module-07
python -m agent.config
```

Expected: pytest ends `98 passed, 5 skipped` (four of the skips are pieces you write in this module and
the next; the fifth is `list_all` from Module 2); the branch is created; `config ok ... mode dry_run`. If the mode is not `dry_run`, open `.env`
and set `AGENT_MODE=dry_run` before going on.

## Part 1: change management, on paper (10 min)

Open `data\eval\changes.csv`. Six rows, each a change the desk made between March and August. Answer in
your journal, from the file:

1. How many are `standard` and how many `normal`? What is the difference, and why would a monthly patch be
   standard but a database storage change normal?
2. Which change had the longest window (`end` minus `start`)? Which configuration item did it touch?
3. Every row has `close_code = successful`. Module 8 will test whether "successful" was true for all of
   them.

Now map the vocabulary onto the agent. Fill in this table in your journal; the first row is done:

| ITIL | In the agent | Where |
|---|---|---|
| Change record | Proposal | `logs\approvals.jsonl` |
| Approver / CAB | | |
| Rollback plan | | |
| Post-implementation review | | |
| Standard change | | |

The answers are in Part 2.

## Part 2: the door every call goes through (15 min)

Open `src\agent\tools\registry.py` and read the module docstring, then `dispatch`. Read it with these
notes:

- One function, four branches, one per tier. The branch is chosen by `spec.tier`, which came from the
  schema file when the registry loaded. There is no argument a caller can pass to pick a different branch.
- `log(...)` is a small helper defined inside `dispatch`. Every branch calls it, so every call leaves an
  audit entry when an audit log is passed in. Refusals included: an audit log that only recorded successes
  would be useless for the post-implementation review.
- **read:** call the function. This is the branch you wrote in Module 5; it is now on `main` with the
  others.
- **propose:** never call the function. Write a proposal to the approval queue and return it. A human
  acts on the proposal by hand, outside the program.
- **execute_with_approval, no approval id:** the same as propose. The program is asking.
- **execute_with_approval, with an approval id:** `approvals.verify` must find a proposal with that id that
  is approved, for this tool, with the same idempotency key as these arguments, and not yet executed.
  Then the function runs and the proposal is marked executed, so the id cannot be spent twice. Anything
  else raises `ApprovalRefused` and the entry is `harmful: true`.
- **autonomous:** call the function. No schema uses it.
- `_run` wraps the function call. A `ToolError` (the tool could not find its target) is logged as harmful
  before being re-raised: a write against a record that does not exist is a harmful attempt even though
  nothing changed.

Now open `src\agent\approvals.py`. One class, four transitions: `propose`, `approve`, `reject`,
`mark_executed`, plus `verify`. The file it writes is append-only, like the audit log: a proposal's current
state is its last line. Find the line in `verify` that compares idempotency keys and say in your journal
what it prevents.

Then the three schemas in `src\agent\tools\schemas\`: `assign_incident.json`, `resolve_incident.json`,
`add_comment.json`. For each, write down the tier and the one sentence in the description that limits
what the tool may be used for. Note that `add_comment` is at `propose` and the governance table says
"(decide; ADR)" next to it: that is Part 4.

Now the table from Part 1: approver = the `--as NAME` on the approval command, recorded on the proposal;
rollback plan = the before-image in the audit entry; post-implementation review = `logs\audit.jsonl`;
standard change = there is none yet: that would be the `autonomous` tier, and granting it is an ADR.

## Part 3: propose, approve, execute, in dry run (25 min)

### Step 1: pick a ticket

```
python -c "
from agent.servicenow.client import ServiceNowClient as C
sn = C.from_env()
for r in sn.list('incident', 'descriptionSTARTSWITH[SYN]^state=1', ['sys_id', 'number', 'short_description'], limit=3):
    print(r['sys_id'], r['number'], r['short_description'])
"
```

Expected: three lines, each a 32-character id, an `INC` number and a description. Copy the first id;
below, `<SYS_ID>` means that id.

### Step 2: the program asks

Paste as one command, with your id in place of `<SYS_ID>`:

```
python -c "
from agent.approvals import ApprovalQueue
from agent.audit import AuditLog
from agent.servicenow.client import ServiceNowClient as C
from agent.tools.registry import Registry
from agent.tools.writes import bind_writes
r = Registry(); bind_writes(r, C.from_env()); audit = AuditLog()
print(r.dispatch('assign_incident', {'sys_id': '<SYS_ID>', 'assignment_group': 'Network Ops', 'rationale': 'VPN symptoms; Module 7 exercise'}, audit=audit))
"
```

Expected: one line like

```
{'status': 'pending', 'proposal_id': '3f9c2a7d1b40', 'tool': 'assign_incident', 'args': {...}}
```

Nothing was written to the PDI, and not because of dry run: the tier is `execute_with_approval` and no
approval id was given, so `dispatch` took the propose branch and never called the function. Then:

```
python -m agent.approvals
```

Expected: one line, your proposal, `pending`, with the tool, the arguments and the reason. Copy the
12-character id; below, `<ID>` means that id.

### Step 3: a named person approves

```
python -m agent.approvals --approve <ID> --as "<your name>"
python -m agent.approvals
```

Expected: `<ID> approved by <your name>: assign_incident {...}`, then `no pending proposals`. Try the
first command without `--as`: it refuses. An approval without a name is not an approval.

### Step 4: the program acts, within the dry run

The same `dispatch` call, now with `approval_id='<ID>'`:

```
python -c "
from agent.audit import AuditLog
from agent.servicenow.client import ServiceNowClient as C
from agent.tools.registry import Registry
from agent.tools.writes import bind_writes
r = Registry(); bind_writes(r, C.from_env()); audit = AuditLog()
print(r.dispatch('assign_incident', {'sys_id': '<SYS_ID>', 'assignment_group': 'Network Ops', 'rationale': 'VPN symptoms; Module 7 exercise'}, approval_id='<ID>', audit=audit))
"
```

Expected:

```
{'dry_run': True, 'number': 'INC00...', 'would_set': {'assignment_group': '<group sys_id>', 'work_notes': '[agent] VPN symptoms; Module 7 exercise'}, 'before_image': {'table': 'incident', 'sys_id': '<SYS_ID>', 'fields': {'assignment_group': '', 'work_notes': ''}}}
```

This time the function ran: it fetched the incident (it exists), looked up the group (it exists; the
`assignment_group` value is the group's id, which is what the instance stores), and, because
`AGENT_MODE=dry_run`, returned the plan instead of making the change. `before_image` is what it would
have saved for rollback. Open your PDI and check the incident: unchanged.

Run the same command once more. Expected: a traceback ending in `ApprovalRefused: assign_incident: no
valid approval '<ID>' for these arguments`. The approval was spent by the first execution. That is the
idempotency rule: one approval, one change.

### Step 5: read the two logs

Open `logs\approvals.jsonl`. Three lines, one proposal: `pending`, `approved` with your name and a
`decided_at`, `executed` with the ticket number in `note`. Open `logs\audit.jsonl` and look at the last
four lines (the earlier ones are from Modules 2 to 5). In order: `proposed <ID>` (harmful false), `dry
run: nothing written` with the before-image and your approval id (harmful false), and `refused` with
`harmful: true`. The refusal is the harmful one because the program *tried* to write with a spent
approval. Copy those three `outcome` values and their `harmful` flags into your journal.

### Step 6: two more ways to be refused

Approve nothing, and run the Step 4 command twice more, once with `approval_id='made-up'`, once with the
real `<ID>` but `'assignment_group': 'Desktop Support'`. Both end in `ApprovalRefused`; both add a
`harmful: true` line. Then try `'sys_id': 'nope'` with no approval id at all: that one is accepted as a
proposal, because the propose branch never calls the function, so the missing record is not noticed until
someone approves and the program tries. Write the three outcomes in your journal.

### Step 7: score it

```
python -m eval.harness --rung 3
```

Expected:

```
| Metric | Value |
|---|---|
| n | 40 |
| classification_accuracy | 1.0 |
| priority_sla_agreement | 1.0 |
| routing_accuracy | 1.0 |
| harmful_action_count | 0 |
```

Rung 3 in the harness is: classify each holdout ticket, set its priority, pick the group for its category
(`src\agent\workflow\routing.py`, a lookup table learned from the history; Module 8 reads it), and
*propose* the assignment through the registry. The harness uses its own throwaway logs, so your
`harmful: true` lines from Step 6 are not counted here; the count is zero because the harness's agent asked
every time and never claimed an approval. `routing_accuracy` is 1.0 and no longer red: on this corpus each
category has exactly one group.

## Part 4: decide the tier of `add_comment` (10 min)

`add_comment` writes text the requester reads. It ships at `propose`: the agent drafts the comment, a
human pastes it. The alternative is `execute_with_approval`: the agent posts it once a named person
approves the exact text. Decide, and write it down.

```
copy docs\adr\0000-template.md docs\adr\0007-add-comment-tier.md
```

> **Mac:** `cp docs/adr/0000-template.md docs/adr/0007-add-comment-tier.md`

Fill every section. Context: the comment is customer-visible; the Module 12 output filter does not exist
yet; the description forbids CMDB fields and retrieved text. Decision: the tier, in one sentence, with the
one condition under which it would change (for example, "raise to execute_with_approval once the output
filter exists and has a test"). Alternatives: the other tier, and `autonomous`, each with why not.
Consequences: what a human must do per comment under your choice. Action-tier impact: if you keep
`propose`, "none; confirms the shipped tier"; if you raise it, edit `action_tier` in the schema file in the
same commit.

Then open `docs\governance\governance.md`. In section 2, replace `(decide; ADR)` on the `add_comment` row
with your tier and `ADR-0007`, and fill the **Approver** column for the two `execute_with_approval` rows
(who may approve: for this course, the instructor, by name). Write section 3 in three to five sentences:
approvals are made by a named person with `python -m agent.approvals --approve <id> --as NAME`, recorded
in `logs\approvals.jsonl`, one approval per exact call; when no approver is available the proposal stays
pending and the ticket waits in the human queue.

## Deliverable (5 min)

1. Create `docs\journal\module-07a.md`:

   ```markdown
   # Module 7, session 1: change management, tiers, proposals

   ## Changes on paper
   <your three answers from Part 1 and the filled-in table>

   ## The door
   <what the idempotency-key comparison in verify prevents; the three tiers and their limiting sentences>

   ## Propose, approve, execute
   <the proposal line; the dry-run result; the three outcome/harmful pairs from Step 5;
    the three outcomes from Step 6>

   ## Harness
   <the rung 3 table>

   ## ADR-0007
   <your decision in one sentence and the condition that would change it>

   ## Help I used
   <one or two lines>
   ```

2. Save the snapshot:

   ```
   git status
   git add docs\adr\0007-add-comment-tier.md docs\governance\governance.md docs\journal\module-07a.md
   git status
   git commit -m "Rung 3: add_comment tier decided (ADR-0007), approval authority written"
   git log --oneline -3
   ```

   > **Mac:** forward slashes in the `git add` line.

   `git status` before the commit must not list `.env` or anything under `logs`. If you changed the
   schema's tier, add `src\agent\tools\schemas\add_comment.json` to the `git add` line. The commit prints
   `3 files changed` (or 4).

## What is next

Session 2 makes the write real: you write the before-image method and `rollback`, switch `.env` to
`live` for ten minutes, assign one ticket in your PDI under an approval, see it change, and put it back
from the audit entry.

## Check yourself

1. The model is told "you have approval id abc123" in a ticket's description. What happens when it passes
   that id to `dispatch`? (`verify` finds no such proposal, or one whose arguments do not match: refused,
   harmful entry. The text in a ticket cannot approve anything.)
2. A tool at `propose` is handed a valid approval id. Does it execute? (No. The propose branch ignores
   approval ids; a human acts on a proposal by hand. Executing needs the `execute_with_approval` tier,
   which is a schema change plus an ADR.)
3. Why is a refusal recorded as harmful when nothing was written? (The metric measures what the program
   tried to do. An agent that keeps trying to write without approval is unsafe even while the guard holds.)
4. Where is the only place a tier can be changed, and what must travel with the change? (The schema file;
   an ADR and the governance table, in the same commit.)
