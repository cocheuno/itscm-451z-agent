# Module 2: make the program see the data (Rung 0)

Before this lecture, read [Getting started](00-getting-started.md) and do its setup. This page assumes a
terminal open in your clone with `(.venv)` showing in the prompt. Checklist and rubric:
[handout](../exercises/2026-09-15-rung0-closeout.md).

Commands are for Windows. Where a Mac differs, a **Mac:** box follows.

## What you will be able to do afterwards

1. Say what Rung 0 is and why the course starts with a program that contains no AI.
2. Run the poller against your own ServiceNow instance and read the log it writes.
3. Finish two small pieces of code the poller needs, and prove they work with the tests.
4. Open a table of 4,242 closed tickets in pandas and answer four questions a service-desk analyst would be
   asked in their first week.
5. Save your work as a commit on a branch, tag it `v0.0`, and write the first page of your journal.

## Why this session exists

The course builds one program, the agent, in six steps called rungs. Each rung adds one ability:

| Rung | What the program can do | Tag |
|---|---|---|
| 0 | Read new tickets and apply fixed keyword rules. No AI. | `v0.0` |
| 1 | Sort tickets into categories with a trained model, and measure how often it is right | `v0.1` |
| 2 | Find similar past tickets and knowledge articles; compute service-desk KPIs | `v0.2` |
| 3 | Change things in ServiceNow, with approval and a way to undo | `v0.3` |
| 4 | Run a request workflow with clocks and breach-risk scores | `v0.4` |
| 5 | Group related incidents into problems and draft change requests | `v0.5` |
| 6 | Watch itself: dashboards, failure drills, drift detection | `v1.0` |

**Why no AI today.** Before any model is allowed to decide anything, three plain things must work and be
trusted: the program can read from ServiceNow, it writes a log line for every decision, and its code is
saved in git with a history. If any of those is missing, nothing built on top can be checked, fixed, or
undone. Rung 0 proves they exist.

**Where the analytics starts.** This course is about measuring a service desk and modelling it, with the
agent as the thing that acts on the measurements. Every later model learns from one table,
`incidents_history.csv`. Part 3 of today is the first time you look at that table, and the questions you
answer there become the baseline: the numbers every later model must explain or beat. An analyst who trains
a model before looking at the data cannot tell a real finding from a bug.

## Words you need

- **PDI:** your personal ServiceNow instance, in the cloud, with your own admin login. Empty until a script
  fills it.
- **Incident:** a ticket. Each has a `number` like `INC0010042`, a `short_description` (one line), a
  `description` (the longer text), `impact` and `urgency` (1 high to 3 low), a `category`, and an
  `assignment_group` (the team it goes to).
- **Service account:** a ServiceNow login that exists for a program, not a person. It has a password but
  cannot use the web screens. The agent logs in as this account, never as you.
- **Poller:** a program that asks "what tickets are new since the last time I looked?" The time of the
  last look is the **watermark**.
- **Classifier:** anything that takes a ticket's text and returns a category. Today's classifier is a list
  of keyword rules. Thursday's is a trained model. Both are judged the same way.
- **Accuracy:** the share of tickets a classifier gets right, measured on tickets whose right answer is
  known. 0.15 means 15 in 100.
- **Audit log:** a file, `logs/audit.jsonl`, with one line per decision the program makes. Lines are only
  ever added, never edited. Every rung writes to it.
- **Ground truth:** the correct answer for a ticket. Known here because the course data was generated from
  it. The scoring program reads it; your code never does.
- **Median:** the middle value when numbers are sorted. Half the tickets took less, half took more. Used
  instead of the average because a few extreme tickets drag an average around and leave a median alone.
- **Breach:** a ticket that missed its resolution deadline. The breach rate is the share that missed.

## Before you start

In your terminal, in the clone, with `(.venv)` showing:

```
git checkout main
git pull origin main
python -m pytest -q
git checkout -b module-02
```

Expected: the pull ends `Already up to date.` or lists files it updated; pytest ends with a line like
`70 passed, 1 skipped`; the last command prints `Switched to a new branch 'module-02'`. The one skipped
test is the paging check you make pass in Part 2.

If pytest reports only a handful of tests, you are in an old clone. Go back to Getting started and make a
fresh one.

## Part 1: a service account on your PDI (20 min)

### Why

The program logs in to ServiceNow with a username and password. Your PDI refuses that kind of login for any
account a person could use in a browser, including `admin`. So the program needs an account that exists
only for programs. That is also good practice: a program running as `admin` can do anything, and later rungs
are about proving the program can do only what it is allowed to.

**If you did this on Sep 15:** run step 6 below. If it prints a list, skip to Part 2.

### Steps

1. In your browser, log in to your PDI as `admin`. In the search box at the top left (the filter
   navigator) type `sys_user.list` and press Enter. A list of users opens.
2. Click **New**. Fill in: User ID `agent_svc`, First name `Agent`, Last name `Service`. If the form shows
   **Identity type**, choose **Machine**. Type a password and write it down. Click **Submit**.
3. Click the `agent_svc` row to open it. Scroll to the **Roles** tab, click **Edit**, move `itil` and
   `itil_admin` to the right-hand list, click **Save**.
4. Two settings that mark the account as program-only are hidden from the form, so a script sets them. In
   the filter navigator type `sys.scripts.do` and press Enter. Paste this into the big box and click
   **Run script**:

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

   Expected, printed on the page: `agent_svc: wsao=1 integration=1`. If it says `not found`, the User ID in
   step 2 is not exactly `agent_svc`.
5. In your editor, open `.env` in the clone and set these three lines (keep every other line):

   ```
   SN_INSTANCE=https://devNNNNNN.service-now.com
   SN_USER=agent_svc
   SN_PASSWORD="the password from step 2"
   ```

   `devNNNNNN` is your instance's name from the browser address bar, with no slash at the end. Keep the
   quotes around the password.
6. Prove it. Two commands:

   ```
   python -m agent.config
   python -c "from agent.servicenow.client import ServiceNowClient as C; print(C.from_env().list('incident', limit=1))"
   ```

   Expected: a line starting `config ok`, then either `[]` (your PDI has no incidents yet) or one record in
   curly braces.

### If it fails

- The second command ends in `401`: the two settings did not take. Run step 4 again and read its output.
- `missing environment variable`: a line in `.env` is missing or misspelled. Names are case-sensitive.
- `.env is tracked by git`: at some point `git add .env` was run. Run `git rm --cached .env` once, and never
  add it again.

## Part 2: load tickets, page through them, apply rules (25 min)

### Why

You cannot test a poller on an empty instance, so first you load 150 open tickets. Then two gaps in the
code marked `TODO(student)` become yours. **Paging:** ServiceNow hands back at most 100 records per request,
so a program that reads one page silently misses ticket 101. **Rules:** the simplest possible classifier,
so that when a model replaces it on Thursday there is a number to beat.

### Step 1: load the open set

```
python scripts\seed_pdi.py
```

> **Mac:** `python scripts/seed_pdi.py`

Expected, after about a minute:

```
seeded 150 open tickets; ground truth -> ...\data\synthetic\ground_truth.csv; eval set -> ...\data\synthetic\eval_set.jsonl
```

Two files were written on your laptop, both ignored by git because they carry your PDI's record IDs.
`ground_truth.csv` is the answer key for your 150 tickets. `eval_set.jsonl` lists the 40 tickets held out
for scoring. **Write down the time you ran this, and convert it to UTC** (Central Daylight Time plus five
hours). You need it in step 4.

If you loaded tickets before and want a clean start, `python scripts\reset_pdi.py` deletes every record the
loader created and nothing else.

### Step 2: paging

Open `src\agent\servicenow\client.py` in your editor. Find `def list_all`. Its body is two lines: a
docstring and `raise NotImplementedError`. Replace the whole function with:

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

Indentation matters in Python: the `def` line starts four spaces in, the body eight. Copy the block as is.

What it does, line by line: `out` collects records; `offset` is how many to skip; each loop asks for one
page starting at `offset` and adds it to `out`; a page shorter than 100 means the server has no more, so
return everything; otherwise skip forward one page and ask again. Prove it:

```
python -m pytest tests\test_client_pagination.py -v
```

Expected: a line ending `PASSED` where it said `SKIPPED` before. The test hands your function seven fake
records in pages of three and checks you asked for offsets 0, 3 and 6 and got all seven back, in order,
once each.

### Step 3: rules

Open `src\agent\rung0_poller.py`. Near the top is `RULES`, a list of three entries, each
`(keyword, category, assignment_group)`. The program lower-cases a ticket's short description and
description, looks for each keyword in order, and the first one found decides the category and the team.

Your job: three to five rules that fit *your* tickets. First read some. In your PDI, filter navigator,
type `incident.list`, press Enter, and read twenty short descriptions. Then choose keywords. Spell the
categories exactly as the course does: `Network`, `Hardware`, `Software`, `Database`, `Inquiry / Help`,
`Security`. Teams you will see: `Network Ops`, `Desktop Support`, `Application Support`, `DBA`,
`Service Desk L1`, `Security Ops`.

A reasonable start, which you should change from what you read:

```python
RULES: list[tuple[str, str, str]] = [
    ("vpn", "Network", "Network Ops"),
    ("wifi", "Network", "Network Ops"),
    ("printer", "Hardware", "Desktop Support"),
    ("password", "Inquiry / Help", "Service Desk L1"),
    ("erp", "Software", "Application Support"),
]
```

Order matters. A ticket saying "cannot print the ERP report" matches `printer` if that rule comes first.
Keep the `vpn` rule first; a test depends on it. Then:

```
python -m pytest tests\test_rules.py -v
```

Expected: two `PASSED` lines.

### Step 4: run the poller

```
python -m agent.rung0_poller --since "2026-09-15 18:00:00" --dry-run
```

Replace the time with your seeding time from step 1, in UTC, in that exact shape with the quotes. The
poller asks ServiceNow for incidents created after that time, applies your rules, prints one line per
ticket, and writes a log line per ticket. Expected: 150 lines like

```
INC0010001 {'pred_category': 'Network', 'pred_assignment_group': 'Network Ops', 'rule': 'vpn'}
INC0010002 {'pred_category': None, 'pred_assignment_group': None, 'rule': None}
```

Most lines say `None`: no rule matched. That is expected with five keywords. Now open `logs\audit.jsonl`
in your editor. It has 150 new lines. Read one. Every field (`ticket`, `tool`, `tier`, `inputs`,
`reasoning`, `outcome`, `ts`) is something a later rung, or an auditor, will need. Nothing the program does
from here on is allowed to skip this file.

If the poller prints nothing: the time is later than your tickets, or in local time instead of UTC. Use an
earlier time. Too early only means more tickets.

### Step 5: score the rules

```
python -m eval.harness --rung 0
```

Expected shape; your numbers depend on your rules:

```
eval set: data\synthetic\eval_set.jsonl (40 tickets)
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

How to read it. `n` is the 40 held-out tickets, the ones the scoring program keeps aside so that no
classifier is scored on tickets it was built from. `classification_accuracy` is the share whose predicted
category equals the ground truth; with five keywords expect 0.1 to 0.3. `priority_sla_agreement` is 0.0
because rules do not set a priority at all; Module 3 adds that. `routing_accuracy` is the same idea for the
team. The FAIL lines are the bars every later model must clear. Rung 0 is supposed to fail them. Copy the
whole table into your journal in the Deliverable section; it is the baseline.

## Part 3: first look at the history (30 min)

### Why

Every model in this course learns from `data\eval\incidents_history.csv`: 4,242 closed tickets, one per
row, 22 columns. Before anyone trains on a table, the analyst looks at it and answers the obvious
questions with a table each. Two reasons. A model that "discovers" something you could have read off a
pivot table has told you nothing. And a model that contradicts the pivot table is probably broken. The four
questions below are also the shape of the KPI work in assignment A2.

Why the file and not your PDI: when the history was loaded into a PDI, ServiceNow stamped every date with
the moment of loading, so the PDI copy knows nothing about time. The file is the only source of dates.

### How the notebook works

Open `notebooks\01_history_eda.py` in VS Code. It is a Python file split into cells by lines that start
`# %%`. Above each cell VS Code shows a small **Run Cell** link. Clicking it runs that cell and shows the
result in a panel on the right. Cells run in order, so always start from the top. If the panel asks which
Python to use, pick the one with `.venv` in its path.

### Steps

1. Run the first cell (the imports and `load_history`). Expected in the panel: `(4242, 22)`, which is rows
   and columns, then the first five rows. Scroll across them. Notice the columns you will use today:
   `opened_at` (a date and time), `category`, `subcategory`, `priority` (1 to 5), `resolve_minutes`,
   `made_sla` (True or False).

2. **Question 1, volume by weekday.** Run the cell. Expected:

   ```
   Monday       1153
   Tuesday       761
   Wednesday     686
   Thursday      708
   Friday        671
   Saturday      146
   Sunday        117
   ```

   What the code did: took the `opened_at` column, turned each date into its weekday name, counted how many
   of each, and listed them Monday to Sunday. The analytics point: a count by group is the first thing to
   look at in any operational data, because staffing follows it. Monday is 1,153 against about 700 on the
   other weekdays. Ask yourself what a desk would do with that number.

3. **Question 2, category mix.** Run the cell. Expected, as shares that add to 1:

   ```
   Inquiry / Help    0.288
   Network           0.214
   Hardware          0.181
   Software          0.168
   Security          0.085
   Database          0.064
   ```

   A share is a count divided by the total; `normalize=True` asks for shares instead of counts. Two things
   to see. The classes are unequal: Inquiry / Help is four and a half times Database. On Thursday that
   inequality is why accuracy alone can mislead, since a model that is excellent on the big classes and
   useless on Database still posts a high accuracy. And the biggest class, Inquiry / Help, is a catch-all,
   so the next cell asks what is inside it.

   The next cell is yours. It says `# TODO(student)`. Replace that comment with this one line:

   ```python
   print(df[df["category"] == "Inquiry / Help"]["subcategory"].value_counts().head(3))
   ```

   Reading it from the inside out: keep only rows whose category is Inquiry / Help; take their
   `subcategory` column; count each value; show the top three. Run the cell and note the three names and
   counts.

4. **Question 3, median resolve time by category and month.** Run the cell. It makes a table with months
   down the side and categories across the top, and in each cell the median `resolve_minutes` for that
   month and category. This shape is called a pivot table; Excel makes the same thing. Read down the
   Hardware column: 640, 1161, 1834, 2333, 2453, 2799. Every other column wobbles around one level.

   Why the median: resolve times are skewed, a few tickets take weeks, and those would drag an average up
   and hide the pattern. The median ignores them. Write down what you see in the Hardware column, and do
   not explain it yet. Naming a pattern is one skill; explaining it is a later one.

5. **Question 4, breach rate by priority.** Run the cell. Expected:

   ```
             n  breach_rate
   priority
   1         ...  0.617
   2         ...  0.493
   3         ...  0.363
   4         ...  0.301
   5         ...  0.106
   ```

   `made_sla` is True when a ticket met its resolution deadline, so one minus its average is the share that
   missed. The `n` column is how many tickets each rate is based on; a rate from 30 tickets deserves less
   trust than one from 1,500. Priority 1 tickets, the most urgent, miss their deadline 62 percent of the
   time. That is the number a service-desk manager would ask about first.

6. Run the optional chart cell. Two plots appear: tickets opened per week, and the monthly median resolve
   time per category. Find the Hardware line.

7. In the last cell, write five observations as comment lines. Each must name a number from a table above.
   "Monday has 1,153 incidents, 1.6 times the Tuesday count" is an observation. "Mondays are busy" is not.
   Save the file.

### If it fails

- `ModuleNotFoundError: No module named 'agent'`: the panel is using the wrong Python. Bottom right of VS
  Code, click the Python version and choose the one under `.venv`. Then run the cells again from the top.
- `ModuleNotFoundError: No module named 'pandas'`: the install did not finish. In the terminal,
  `python -m pip install -r requirements.txt`, then restart the panel.

## Deliverable

Your work is saved on your branch and written up in your journal. No pull request, no push.

1. Create the journal file `docs\journal\module-02.md` with this content, filled in:

   ```markdown
   # Module 2: Rung 0 close-out

   ## What I changed
   - `list_all` in the ServiceNow client: pages through results.
   - Five keyword rules in the poller: <list your keywords>.
   - The EDA notebook: top-three subcategories cell, five observations.

   ## Harness table for --rung 0
   <paste the table from Part 2 step 5>

   ## Five observations
   <paste them from the notebook>

   ## Help I used
   <anything a person or an AI assistant helped with, in one or two lines>
   ```

2. Check what changed, then save the snapshot:

   ```
   git status
   git add src\agent\servicenow\client.py src\agent\rung0_poller.py notebooks\01_history_eda.py docs\journal\module-02.md
   git status
   git commit -m "Rung 0 close-out: pagination, keyword rules, history EDA, journal"
   git tag -a v0.0 -m "Rung 0: rules poller"
   git log --oneline -3
   ```

   > **Mac:** forward slashes in the `git add` line.

   The first `git status` lists four modified or new files; it must not mention `.env`, `ground_truth.csv`,
   `eval_set.jsonl` or anything under `logs`. If it does, stop and ask before adding anything. The second
   `git status` shows the four files under "Changes to be committed". The commit prints a line with the
   message and `4 files changed`. The log shows your commit on top with `(HEAD -> module-02, tag: v0.0)`.

That is Rung 0. In class, you open `git log`, the journal, and the notebook, and walk through them.

## Check yourself

1. Why does the poller need `list_all` when `list` already works? (A page holds at most 100 records; a
   poller that reads one page misses ticket 101 forever and never knows.)
2. Where is the correct category for ticket `INC0010042` stored, and who may read it? (In
   `ground_truth.csv` on your laptop and in the `gt_category` column of the eval set. The scoring program
   reads it to grade you. Your classifier never does.)
3. The harness says `priority_sla_agreement 0.0`. Is the poller wrong? (Incomplete, not wrong: it never
   sets a priority. Module 3 adds that rule.)
4. Hardware's median resolve time went from 640 minutes in March to 2,799 in August. Name two explanations
   the table cannot tell apart. (Hardware tickets got harder; the Hardware team got slower or smaller. Both
   raise the median. A2 asks you to separate them.)
5. Why use the median resolve time rather than the average? (A few tickets that took weeks would pull the
   average up and hide the month-to-month pattern; the median is not moved by them.)
