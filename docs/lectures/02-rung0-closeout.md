# Module 2 close-out: make the agent see the data (Rung 0)

Delivered Tuesday, Sep 15. Rewritten Sep 19 as a complete walkthrough, because the session was spent
re-cloning and most of the steps below were not reached. Work through it in order before Module 4 starts on
Sep 22. Checklist and rubric: [handout](../exercises/2026-09-15-rung0-closeout.md).

## What you will be able to do afterwards

1. Explain what Rung 0 of the agent is and why the course starts with a program that has no AI in it.
2. Run the poller against your own ServiceNow instance and read its audit log.
3. Finish two pieces of code the poller needs (paging through results, keyword rules) and prove they work
   with tests.
4. Load a CSV of 4,242 closed incidents into pandas and answer four questions about the service desk.
5. Push the work as a pull request and tag the result `v0.0`.

## Why this session exists

The course builds one agent in six rungs. Each rung adds one capability and is tagged when it is done:

| Rung | What the agent can do | Tag |
|---|---|---|
| 0 | Read new tickets and apply fixed keyword rules. No AI. | `v0.0` |
| 1 | Classify tickets with trained models and score itself against ground truth | `v0.1` |
| 2 | Retrieve similar incidents and knowledge articles; compute KPIs | `v0.2` |
| 3 | Take actions in ServiceNow, under approval and with rollback | `v0.3` |
| 4 | Run a request workflow with SLA timers and breach-risk scoring | `v0.4` |
| 5 | Cluster incidents into problems and draft change requests | `v0.5` |
| 6 | Watch itself: dashboards, failure injection, drift detection | `v1.0` |

Rung 0 has no AI on purpose. Before a model is allowed to make a decision, three plumbing pieces must
exist and be trusted: the agent can **read from ServiceNow**, it **writes an audit entry for every decision**,
and its code **reaches `main` only through a pull request**. If any of these is missing, nothing built on top
can be graded, debugged, or rolled back. Rung 0 is the proof that they exist.

**Where analytics fits.** The course has three threads: the capability ladder above, version management (every
assignment is a merged pull request plus a Git tag), and analytics (the agent measures and models the desk it
runs). The analytics thread starts today in Part 3. Before anyone trains a model on this data, the analyst
looks at it. The four questions in Part 3 are the questions a new service-desk analyst would be asked in their
first week, and their answers become the baseline every later model is compared against.

## Words you need

- **PDI**: your personal developer instance of ServiceNow. It is a real ServiceNow, empty until you load it.
- **Incident**: a ticket. The `incident` table holds them. Each has a `sys_id` (a 32-character unique key),
  a `number` like `INC0010042`, a `short_description`, a `description`, `impact` and `urgency` (1 to 3),
  a `category`, and an `assignment_group`.
- **Table API**: ServiceNow's REST interface. `GET /api/now/table/incident?sysparm_limit=100` returns up to
  100 incidents as JSON. The agent's client wraps this in `src/agent/servicenow/client.py`.
- **Service account**: a ServiceNow user that exists for a program, not a person. It has a password but
  cannot log in to the web interface.
- **Poller**: a program that asks "what is new since the last time I looked?" on a schedule. The watermark is
  the timestamp of the last look.
- **Audit log**: an append-only file, one JSON line per decision, in `logs/audit.jsonl`. Every rung writes
  to it. Never edited by hand.
- **Corpus**: the synthetic data set the course runs on. `data/eval/incidents_history.csv` holds 4,242 closed
  incidents from March to August 2026; `data/eval/incidents_open.csv` holds 150 open ones for September.
- **Ground truth**: the correct answer for a ticket, known because the data was generated from it. In the
  open set these are the `gt_*` columns. Grading uses them; your code never reads them while classifying.

## Before you start

You need the fresh clone from the [handout](../exercises/2026-09-15-rung0-closeout.md) section "Update your
clone". Prove it, in a terminal inside the `itscm-451z-agent` folder with the virtual environment active
(the prompt shows `(.venv)`):

```
git log --oneline -1
pytest -q
```

Expected: the first line shows a recent merge commit from `cocheuno/itscm-451z-agent`, and pytest ends with
`passed` and `1 skipped`. The exact count grows as the repo grows; the skip is the pagination test you turn
green in Part 2. If pytest reports 6 tests, you are in the old folder; go back to the handout.

## Part 1: a service account on your PDI (20 min)

### Why

The agent talks to ServiceNow with a username and password over HTTPS ("basic auth"). Your PDI refuses basic
auth for any account that can log in interactively, including `admin`; the instance log shows the refusal as
`SNCRestrictBasicAuthUserAuthenticationGate`. So the agent needs an account that exists only for programs.
This is also the right posture: an agent that runs as `admin` can do anything, and later rungs are about
proving it can do only what it is allowed to do.

### Steps

1. Log in to your PDI as `admin` in the browser. In the filter navigator (the search box top left) type
   `sys_user.list` and press Enter. This opens the user table.
2. Click **New**. Fill in: User ID `agent_svc`, First name `Agent`, Last name `Service`. If the form shows
   **Identity type**, choose **Machine**. Set a password (write it down; you need it in step 5). Submit.
3. Open the record you just made. Scroll to **Roles**, click **Edit**, add `itil` and `itil_admin`, Save.
   `itil` lets the account read and update incidents; `itil_admin` adds the tables later rungs need.
4. The form hides the two flags that mark the account as non-interactive, so set them with a script. In the
   filter navigator type `sys.scripts.do` and press Enter. Paste this into the box and click **Run script**:

   ```javascript
   var gr = new GlideRecord('sys_user');
   if (gr.get('user_name', 'agent_svc')) {
     gr.setValue('web_service_access_only', true);
     gr.setValue('internal_integration_user', true);
     gr.setValue('locked_out', false);
     gr.setValue('password_needs_reset', false);
     gr.update();
     gs.info('agent_svc: wsao=' + gr.getValue('web_service_access_only') +
             ' integration=' + gr.getValue('internal_integration_user'));
   } else {
     gs.info('agent_svc not found');
   }
   ```

   Expected output on the page: `agent_svc: wsao=1 integration=1`. If it says `not found`, the User ID in
   step 2 is not exactly `agent_svc`.
5. In the repo, open `.env` (create it with `cp .env.example .env` if it does not exist). Set:

   ```
   SN_INSTANCE=https://devNNNNNN.service-now.com     # your instance, no trailing slash
   SN_USER=agent_svc
   SN_PASSWORD="the password from step 2"
   ```

   Leave the other lines as they are for now. `.env` is git-ignored; it never leaves your laptop.
6. Prove it works. Two commands:

   ```
   python -m agent.config
   python -c "from agent.servicenow.client import ServiceNowClient as C; print(C.from_env().list('incident', limit=1))"
   ```

   Expected: `config ok — instance https://devNNNNNN.service-now.com, model claude-sonnet-4-6, mode dry_run`,
   then `[]` (an empty list, because your PDI has no incidents yet) or one record in braces.

### If it fails

- `401` in the second command: the flags did not take. Re-run step 4 and read its output line. If the
  password has a `#` or `"` in it, wrap the whole value in double quotes in `.env`.
- `missing environment variable`: the `.env` line is missing or misspelled. Names are case-sensitive.
- The first command says `.env is tracked by git`: you ran `git add .env` at some point. Run
  `git rm --cached .env` and never add it again.

## Part 2: seed, paginate, poll (25 min)

### Why

The poller cannot be tested against an empty instance, so first you load the 150 open tickets. Then two
`TODO(student)` markers in the code become yours: **paging** (the API returns at most a page at a time, and
a poller that reads only the first page silently misses tickets) and **rules** (the simplest possible
classifier, so that when a model replaces it on Thursday there is a number to beat).

### Step 1: load the open set

```
python scripts/seed_pdi.py
```

Expected output (paths will be yours):

```
seeded 150 open tickets; ground truth -> .../data/synthetic/ground_truth.csv; eval set -> .../data/eval/eval_set.jsonl
```

Two files were written on your laptop. `ground_truth.csv` maps each ticket in your PDI to its correct answers
(git-ignored; it is the answer key). `eval_set.jsonl` is the 40 tickets held out for scoring; the number is
40 rather than exactly 30 because the 20 percent holdout is drawn ticket by ticket with a fixed seed. Note
the time you ran this; it is the watermark for step 4.

If you have seeded before and want a clean start: `python scripts/reset_pdi.py` deletes every record the
seeder created (they all start with the `[SYN]` marker) and nothing else.

### Step 2: paging

Open `src/agent/servicenow/client.py`. `list()` fetches one page; `list_all()` is the TODO. Replace its
body with:

```python
    def list_all(self, table: str, query: str = "", fields: list[str] | None = None, page: int = 100) -> list[dict]:
        """Fetch every matching record by paging until a page comes back shorter than `page`."""
        out: list[dict] = []
        offset = 0
        while True:
            batch = self.list(table, query, fields, limit=page, offset=offset)
            out.extend(batch)
            if len(batch) < page:
                return out
            offset += page
```

Line by line: `out` accumulates records; `offset` is how many to skip; each loop asks for one page starting
at `offset`; a page shorter than `page` means the server ran out, so return; otherwise move the offset by one
page. The acceptance test was written before you started:

```
pytest tests/test_client_pagination.py -v
```

Expected: `PASSED` (it was `SKIPPED` before). The test feeds seven fake records in pages of three and checks
you asked for offsets 0, 3 and 6 and got all seven back, in order, once each.

### Step 3: rules

Open `src/agent/rung0_poller.py`. `RULES` is a list of `(keyword, category, assignment_group)`. Three are
there as examples. The rule is: lower-case the ticket's short description plus description, and the first
keyword found wins. Your job is three to five rules that are true of *your* tickets, so look at them first.
In your PDI, open the incident list (filter navigator: `incident.list`), sort by number, and read twenty
short descriptions. Then choose keywords. Category values must be spelled exactly as the course uses them:
`Network`, `Hardware`, `Software`, `Database`, `Inquiry / Help`, `Security`. Assignment groups you will see in
the data: `Network Ops`, `Desktop Support`, `Application Support`, `DBA`, `Service Desk L1`, `Security Ops`.

A reasonable set, which you should change based on what you read:

```python
RULES: list[tuple[str, str, str]] = [
    ("vpn", "Network", "Network Ops"),
    ("wifi", "Network", "Network Ops"),
    ("printer", "Hardware", "Desktop Support"),
    ("password", "Inquiry / Help", "Service Desk L1"),
    ("erp", "Software", "Application Support"),
]
```

Order matters: a ticket saying "cannot print the ERP report" matches `printer` if that rule comes first. Run
`pytest tests/test_rules.py` to confirm the two existing tests still pass (the first rule must still send
"VPN drops" to Network).

### Step 4: run the poller

```
python -m agent.rung0_poller --since "2026-09-15 18:00:00" --dry-run
```

Replace the timestamp with the time you seeded, in UTC, in that format. The poller asks ServiceNow for
incidents created after the watermark, applies the rules, prints one line per ticket, and writes an audit
entry per ticket. Expected: 150 lines like

```
INC0010001 {'pred_category': 'Network', 'pred_assignment_group': 'Network Ops', 'rule': 'vpn'}
INC0010002 {'pred_category': None, 'pred_assignment_group': None, 'rule': None}
```

Most lines will say `None`. That is the point. Now look at the audit log: `logs/audit.jsonl` has 150 new
lines. Open one. Every field in it (`ticket`, `tool`, `tier`, `inputs`, `reasoning`, `outcome`, `ts`) is
something a later rung, or an auditor, will need. Nothing the agent does from here on is allowed to skip
this file.

If the poller returns nothing: the watermark is after your seeding time, or is in local time rather than
UTC. ServiceNow stores UTC. Use an earlier time; too early only means more tickets.

### Step 5: score the rules

```
python -m eval.harness --rung 0
```

Expected shape:

```
| Metric | Value |
|---|---|
| n | 40 |
| classification_accuracy | 0.15 |
| priority_sla_agreement | 0.0 |
| routing_accuracy | 0.15 |
| harmful_action_count | 0 |

- FAIL classification_accuracy: 0.15 vs threshold 0.8
- FAIL priority_sla_agreement: 0.0 vs threshold 0.9
- FAIL routing_accuracy: 0.15 vs threshold 0.75
```

Read it this way. `n` is the 40 held-out tickets. `classification_accuracy` is the share whose predicted
category equals the ground truth; with three to five keywords expect 0.1 to 0.3. `priority_sla_agreement` is
0.0 because the rules do not set a priority at all; Module 3 fixes that. `routing_accuracy` is about the
assignment group. The FAIL lines are the thresholds the models must clear later. A Rung 0 run is supposed to
fail them; write the table into your PR anyway, it is the baseline.

## Part 3: first look at the history (30 min)

### Why

Every model in this course is trained on `incidents_history.csv`. Before training anything, the analyst
answers four questions with a table each, because a model that "discovers" something you could have read
from a pivot table has told you nothing, and a model that contradicts the pivot table is probably wrong. The
four questions are also the shape of the KPI work in A2.

Why the CSV and not your PDI: the instance overwrites every timestamp with the moment you loaded the record,
so the PDI copy of the history knows nothing about time (ADR-0002 records this). The CSV is the only source
of time.

### Steps

1. In VS Code, open `notebooks/01_history_eda.py`. It is a script with `# %%` markers; VS Code shows a
   **Run Cell** link above each one. Click the first (the imports and `load_history`). The interactive window
   opens and prints `(4242, 22)`: 4,242 rows, 22 columns.
2. Run the Question 1 cell. Expected:

   ```
   Monday       1153
   Tuesday       761
   Wednesday     686
   Thursday      708
   Friday        671
   Saturday      146
   Sunday        117
   ```

   The code: `df["opened_at"].dt.day_name()` turns each timestamp into a weekday name; `.value_counts()`
   counts them; `.reindex([...])` puts the days in calendar order instead of largest-first.
3. Run the Question 2 cell. Expected: `Inquiry / Help 0.288`, `Network 0.214`, `Hardware 0.181`,
   `Software 0.168`, `Security 0.085`, `Database 0.064`. `value_counts(normalize=True)` gives shares
   instead of counts. The next cell is yours: the top three subcategories inside `Inquiry / Help`. One line
   does it: `df[df["category"] == "Inquiry / Help"]["subcategory"].value_counts().head(3)`.
4. Run the Question 3 cell. It adds a `month` column and pivots: rows are months, columns are categories,
   cells are the median `resolve_minutes`. Read down the Hardware column: 640, 1161, 1834, 2333, 2453, 2799.
   Every other column wobbles around a level. Write down what you see; do not explain it yet.
5. Run the Question 4 cell. `made_sla` is True when the ticket met its resolution target; `1 - mean` is the
   breach rate. Expected: P1 0.617, P2 0.493, P3 0.363, P4 0.301, P5 0.106.
6. Run the optional chart cell if matplotlib is installed. Two plots appear in the interactive window.
7. In the last cell, write five observations. Each must name a number from a table above. "Monday has 1,153
   incidents, 1.6 times the Tuesday count" is an observation. "Mondays are busy" is not.

### If it fails

- `ModuleNotFoundError: agent`: the interactive window is using the wrong Python. Bottom right of VS Code,
  click the interpreter and pick `.venv`. Or run `pip install -e .` in the terminal and restart the window.
- `ModuleNotFoundError: pandas`: `pip install -r requirements.txt` did not finish. Run it again and read
  the last error.

## Deliverable

One pull request. Step by step:

```
git checkout -b feature/rung0-closeout
git add src/agent/servicenow/client.py src/agent/rung0_poller.py notebooks/01_history_eda.py
git status
```

`git status` must not list `.env`, `ground_truth.csv`, `eval_set.jsonl` or anything under `logs/`. If it
does, stop and ask. Then:

```
git commit -m "Rung 0 close-out: pagination, keyword rules, history EDA"
git push -u origin feature/rung0-closeout
```

The push prints a link to open the pull request. Open it, and fill in the template: Rung 0; what changed
(three things); the harness table from Part 2 step 5 pasted into "Eval results"; "ADRs touched: none"; tick
the checklist honestly; disclose any AI help. Mark it ready for review. When the instructor merges:

```
git checkout main
git pull origin main
git tag -a v0.0 -m "Rung 0: rules poller"
git push origin v0.0
```

The tag is the record that Rung 0 exists. Every later rung gets one.

## Check yourself

1. Why does the poller need `list_all` when `list` already works? (A page is at most 100 records; a poller
   that reads one page misses ticket 101 forever and never knows.)
2. Where is the correct category for ticket `INC0010042` stored, and who may read it? (In
   `data/synthetic/ground_truth.csv` on your laptop and in the `gt_category` column of the eval set. The
   harness reads it to score you. Your classifier never does.)
3. The harness says `priority_sla_agreement 0.0`. Is the poller wrong? (It is incomplete: it never sets a
   priority. Module 3 adds the rule.)
4. Hardware's median resolve time went from 640 minutes in March to 2,799 in August. Name two explanations
   the table cannot distinguish between. (Hardware tickets got harder; the Hardware team got slower or
   smaller. Both raise the median. A2 asks you to tell them apart.)
