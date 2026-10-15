# Module 7, session 2: the before-image, rollback, and one real write

Before this lecture: session 1 is committed on your `module-07` branch, with ADR-0007 and the governance
sections. About 50 minutes of guided work. Commands are for Windows; a **Mac:** box follows where a command
differs. `.env` says `AGENT_MODE=dry_run` when you start and when you finish.

## What you will be able to do afterwards

1. Write the two functions that make a write reversible: the before-image read and `rollback`.
2. Explain why a write without a before-image is forbidden, in change-management terms.
3. Make one approved change in your PDI through the program, see it in the instance, and put it back from
   the audit entry.
4. Read the audit log as a post-implementation review: which writes, by whom, and how many were harmful.

## Where the repository already stands

| Item | On `main`? | What you do |
|---|---|---|
| `ServiceNowClient.update_with_before_image` | No, marked `TODO(student)` | Write it (Part 1) |
| `writes.rollback` | No, marked `TODO(student)` | Write it (Part 2) |
| Everything the two functions are called from | Yes | Run it live, once (Part 3) |

## Why this session exists

**ITSM.** A change without a rollback plan is not approved. CABs reject them. The agent's rollback plan is
the before-image: the fields it is about to change, read a moment before it changes them, stored in the
audit entry. Today you write the read and the restore, and you see both work on one incident in your PDI.
The write tools refuse to go live until the before-image method exists; that refusal is the rule in code.

**The capability ladder.** Rung 3's four words were tiers, approvals, audit, rollback. Session 1 covered
the first three. Rollback is the last and the one that makes the others safe to use: an approval can be
wrong, and the audit log says what to undo.

**Analytics.** Small today: the audit log is a table, and at the end you summarise it with the same
`groupby` you used on the history in Module 2. Module 8 is the analytics-heavy session.

## Words you need

- **Before-image:** the values of the fields a write will change, read just before the write. The
  after-image is the same fields afterwards.
- **PATCH:** the HTTP verb for "change these fields on this record". `client.update` sends it.
- **Journal field:** `work_notes` and `comments` on an incident are not plain fields. A PATCH *appends* an
  entry; reading the field back gives an empty string. Their before-image is therefore empty, and
  restoring it writes nothing, which is correct: you cannot un-say a note, and nobody should try.
- **Live:** `AGENT_MODE=live`. Approved writes reach the PDI. Set it for Part 3 and unset it after.

## Before you start

```
git status
git log --oneline -2
python -m pytest tests\test_writes.py -v
```

Expected: nothing to commit; your session-1 commit on top; five `PASSED` and one `SKIPPED` named
`test_rollback_restores_the_before_image`.

## Part 1: the before-image read (10 min)

Open `src\agent\servicenow\client.py`, find `def update_with_before_image`. Its body is a docstring and
`raise NotImplementedError`. Replace the whole function with:

```python
    def update_with_before_image(self, table: str, sys_id: str, payload: dict) -> tuple[dict, dict]:
        """Read the fields in payload as they are now, PATCH them, and return (before, after)."""
        before = self.get(table, sys_id, list(payload))
        after = self.update(table, sys_id, payload)
        return before, after
```

The `def` line starts four spaces in, the body eight. Line by line: `list(payload)` is the list of field
names about to change; `self.get` reads exactly those fields from the record as it is now; `self.update`
makes the change; both dictionaries go back to the caller. The read comes first on purpose. If the PATCH
fails, nothing was changed and the before-image is simply unused; if the read failed, the function would
have stopped before changing anything. There is no order in which a change can happen without its
before-image having been captured.

```
python -m pytest tests\test_servicenow_client.py -v
```

Expected: the test named `test_update_with_before_image_reads_then_patches` now `PASSED` instead of
`SKIPPED`. It hands the client a fake instance and checks that a GET for the right fields happened before
the PATCH, and that both results come back.

## Part 2: rollback (10 min)

Open `src\agent\tools\writes.py`, find `def rollback`. Replace the whole function with:

```python
def rollback(sn, before_image: dict, *, live: bool = False) -> dict:
    """Put the fields in before_image back the way they were: the rollback plan, executed."""
    fields = before_image["fields"]
    if not live:
        return {"dry_run": True, "would_set": fields}
    sn.update(before_image["table"], before_image["sys_id"], fields)
    return {"dry_run": False, "set": fields}
```

`before_image` is the dictionary every write tool returns and every executed audit entry stores: the
table, the record id, and the fields with their old values. Rollback is a PATCH of those old values. It
has no schema file and is not in the registry on purpose: it is a human's action, taken from the audit
log, never something the model can call. Notice it goes through `sn.update`, not through
`update_with_before_image`: the rollback of a rollback is the original write, which the audit log already
holds.

```
python -m pytest tests\test_writes.py -v
```

Expected: six `PASSED`, no skips.

## Part 3: one real write, and back (25 min)

### Step 1: go live, for this part only

Open `.env`, change `AGENT_MODE=dry_run` to `AGENT_MODE=live`, save. Then:

```
python -m agent.config
```

Expected: `config ok ... mode live`.

### Step 2: propose and approve

Use the same `<SYS_ID>` as session 1. Paste as one command:

```
python -c "
from agent.audit import AuditLog
from agent.servicenow.client import ServiceNowClient as C
from agent.tools.registry import Registry
from agent.tools.writes import bind_writes
r = Registry(); bind_writes(r, C.from_env()); audit = AuditLog()
print(r.dispatch('assign_incident', {'sys_id': '<SYS_ID>', 'assignment_group': 'Network Ops', 'rationale': 'VPN symptoms; Module 7 live exercise'}, audit=audit))
"
python -m agent.approvals
python -m agent.approvals --approve <ID> --as "<your name>"
```

Expected: a `pending` proposal, its id listed, then `approved by <your name>`. Live mode changed nothing
here: the propose branch never calls the function.

### Step 3: execute

```
python -c "
from agent.audit import AuditLog
from agent.servicenow.client import ServiceNowClient as C
from agent.tools.registry import Registry
from agent.tools.writes import bind_writes
r = Registry(); bind_writes(r, C.from_env()); audit = AuditLog()
print(r.dispatch('assign_incident', {'sys_id': '<SYS_ID>', 'assignment_group': 'Network Ops', 'rationale': 'VPN symptoms; Module 7 live exercise'}, approval_id='<ID>', audit=audit))
"
```

Expected:

```
{'dry_run': False, 'number': 'INC00...', 'set': {'assignment_group': '<group id>', 'work_notes': '[agent] VPN symptoms; Module 7 live exercise'}, 'before_image': {'table': 'incident', 'sys_id': '<SYS_ID>', 'fields': {'assignment_group': '', 'work_notes': ''}}, 'after': {'assignment_group': '<group id>', 'work_notes': ''}}
```

Now open the incident in your PDI (filter navigator `incident.list`, find the number). **Assignment
group** reads `Network Ops`. Open the **Notes** tab: a work note starting `[agent]` with your rationale,
by `agent_svc`. That is the first record the program has ever changed. The `after` shows `work_notes` as
empty: journal field, see Words you need.

If instead you see a traceback ending `NotImplementedError`, Part 1 is not saved, or the terminal is in
another folder. If it ends `403`, the service account lacks write rights on `incident`: `itil` is enough
for assignment; check the role in the PDI, then run Step 3 again with a new proposal and approval (the
first approval was spent by the attempt; its audit entry says `refused`, harmful, and that is correct).

### Step 4: roll it back

The before-image is in the last audit entry. Read it from there, not from the terminal, because that is
where an operator would find it next week:

```
python -c "
from agent.audit import AuditLog
from agent.servicenow.client import ServiceNowClient as C
from agent.tools.writes import rollback
entry = [e for e in AuditLog().read() if e['outcome'] == 'executed'][-1]
print('undoing', entry['tool'], 'on', entry['ticket'], 'approved as', entry['approval_id'])
print(rollback(C.from_env(), entry['before_image'], live=True))
"
```

Expected: the `undoing` line, then `{'dry_run': False, 'set': {'assignment_group': '', 'work_notes': ''}}`.
Reload the incident in the PDI: **Assignment group** is empty again; the work note is still there (journal
fields are append-only; the restore wrote nothing to it). Both the change and the reversal are in the
instance's own history for the record (the **History** related list), which is the independent record a
reviewer would compare against your audit log.

### Step 5: back to dry run

Open `.env`, set `AGENT_MODE=dry_run`, save, and prove it:

```
python -m agent.config
```

Expected: `mode dry_run`. Do this before anything else. A laptop left in live mode is the kind of thing
section 5 of the governance document exists to forbid.

## Part 4: the audit log as a review (5 min)

```
python -c "
import pandas as pd
from agent.audit import AuditLog
df = pd.DataFrame(AuditLog().read())
print(df.groupby(['tool', 'tier', 'harmful']).size().to_string())
print()
print(df[df.tier != 'read'][['ticket', 'tool', 'outcome', 'approval_id', 'harmful']].tail(8).to_string(index=False))
"
```

Expected: the first table counts every entry since Module 2 by tool, tier and harmful flag (the `rules`
and `classify_incident` rows from the poller are large; `assign_incident` has a handful, two to four of
them harmful from session 1 Step 6). The second lists your last eight write-tier entries: proposals,
one dry run, one executed, and the refusals. This is the post-implementation review of everything the
program has tried to change, and it took two lines of pandas because the log is a table.

## Deliverable (5 min)

1. Create `docs\journal\module-07b.md`:

   ```markdown
   # Module 7, session 2: before-image, rollback, one real write

   ## The two functions
   <why the read comes before the PATCH, in your words; why rollback is not a registered tool>

   ## The live write
   <the executed result; what the PDI showed; the rollback result; what the PDI showed after>

   ## The review
   <the groupby table; how many harmful entries you have and what each was>

   ## Help I used
   <one or two lines>
   ```

2. Save the snapshot:

   ```
   git status
   git add src\agent\servicenow\client.py src\agent\tools\writes.py docs\journal\module-07b.md
   git status
   git commit -m "Rung 3: before-image capture and rollback; one approved live write verified"
   git log --oneline -3
   ```

   > **Mac:** forward slashes in the `git add` line.

   `git status` before the commit must not list `.env` or `logs`. The commit prints `3 files changed`.

## What is next

Module 8 is the analytics half of A3. Session 1: the KPI functions (MTTR, SLA attainment, backlog aging,
category Pareto) as the desk's descriptive baseline, then a diagnostic question with a method behind it:
which of the six changes in `changes.csv` caused incidents, how many, and how sure can you be. Session 2:
governance v1, models as change-managed artifacts, the harness gate, and tag `v0.3`. Module 8 continues
on this branch.

## Check yourself

1. The PATCH succeeds but the program crashes before the audit entry is written. Is the change
   recoverable? (From the instance's own history, yes; from the agent's log, no. That gap is the Module 14
   failure scenario `process_kill_mid_workflow`; the fix is to write the audit entry with the before-image
   before the PATCH and update it after.)
2. Why does `rollback` call `update` rather than `update_with_before_image`? (The before-image of a
   rollback is the write it undoes, already in the log.)
3. A colleague suggests the model should be allowed to call `rollback` when it thinks it made a mistake.
   What tier would that need, and what else? (A schema at `execute_with_approval` at least, an ADR, a
   governance row; and the point of rollback is that a human decides a change was wrong.)
