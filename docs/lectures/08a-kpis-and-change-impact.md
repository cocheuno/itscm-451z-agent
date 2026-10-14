# Module 8, session 1: the desk's KPIs, and did a change cause incidents?

Before this lecture: Module 7 is committed on your `module-07` branch (two commits). Module 8 continues
on the same branch; A3 is both modules. About 75 minutes of guided work, most of it analytics. Commands
are for Windows; a **Mac:** box follows where a command differs.

## What you will be able to do afterwards

1. Produce the five KPI tables a service-desk manager asks for and say what each one measures.
2. State the difference between descriptive and diagnostic analytics with one example of each from today.
3. Write the baseline function of the change-impact method and explain each line.
4. Read the change-impact table, name the change that caused incidents, and defend the claim with three
   kinds of evidence: the count, the category, the text.
5. Spot the small-numbers trap: a big ratio on a handful of tickets.

## Where the repository already stands

| Item | On `main`? | What you do |
|---|---|---|
| `src\agent\analytics\kpi.py`, five KPI functions and a report | Yes | Run and read (Part 1) |
| `src\agent\workflow\routing.py`, the routing table | Yes | Read (Part 1) |
| `src\agent\analytics\change_impact.py`, the method | Yes, except one function | Read (Part 2) |
| `expected_count` in that file | No, marked `TODO(student)` | Write it (Part 3) |
| The memo `docs\memos\2026-10-22-a3-change-impact.md` | No | Draft it (Part 5) |

## Why this session exists

**Analytics.** Everything so far described the past (how many tickets, how slow) or predicted a label
(which category). Today is the third kind, **diagnostic** analytics: *why* did something happen. The
question is the one a change manager asks after every maintenance window: did ticket volume go up
afterwards, by how much more than it would have anyway, and in which categories. The method is a
comparison of two counts with two refinements, and you write the piece that makes it work: the baseline.

**ITSM.** Change management does not end when the change closes. The post-implementation review asks
whether the change did what it promised and nothing else. All six changes in `changes.csv` were closed
`successful`. Today's table says whether that was true.

**The capability ladder.** Rung 3's write tools need somewhere to send tickets. `routing.py` is the
simplest routing model there is, learned from the history, and it is what the harness has been scoring
as `routing_accuracy` since Module 7.

## Words you need

- **Descriptive analytics:** what happened. The KPI tables.
- **Diagnostic analytics:** why it happened. Comparing a window after an event with what would have
  happened without it.
- **MTTR:** mean time to resolve. The median is reported beside it because a few very slow tickets drag
  the mean up: here the mean is four times the median.
- **SLA attainment:** the share of tickets that met their resolution target (`made_sla`).
- **Backlog aging:** how long the open tickets have been waiting, in buckets.
- **Pareto:** sorted largest first with a running share, to see how few categories make most of the work.
- **Window:** the hours after a change ends in which its incidents are expected to appear. 72 by default.
- **Baseline:** the period before the change used to estimate normal volume. 28 days by default: four
  whole weeks, so each weekday appears four times and the Monday peak does not bias the estimate.
- **Expected count:** baseline tickets per hour, times the window's hours. What the window would hold on
  a normal week.
- **Ratio** (lift): observed divided by expected. 1.0 is nothing happened.
- **Surprise:** of the windows of the same length inside the baseline, one starting each day, the share
  that held at least as many tickets as the observed window. 0.0: the baseline never did this. 0.3: it
  does this a third of the time, so the ratio is noise.

## Before you start

```
git status
git log --oneline -3
python -m pytest -q
```

Expected: nothing to commit; your two Module 7 commits on top; `passed` with `3 skipped`. If the
instructor has announced an update since Module 7, bring it in without leaving your branch:

```
git checkout main
git pull origin main
git checkout module-07
git merge main
```

Expected: the last command prints `Merge made by the 'ort' strategy` and a file list, or
`Already up to date`. If it says `CONFLICT`, stop and ask; that is a conversation, not a command.

## Part 1: the KPIs (15 min)

```
python -m agent.analytics.kpi
```

Expected: six tables. Read them with these notes; the numbers below are from the committed history.

- **MTTR overall:** median 417.5 minutes, mean 1,795.8. Same tickets, two summaries, a factor of four
  apart. The mean is pulled by the slowest tickets; the median is the typical ticket. Report both, say
  which you mean.
- **MTTR by category:** Hardware median 2,013 against Security 280. Hardware tickets take seven times as
  long to resolve as Security tickets.
- **Median resolve minutes by month and category:** read down the Hardware column: 640, 1,161, 1,834,
  2,333, 2,453, 2,799. It gets slower every month; you noticed this in Module 2. Now read down Network:
  flat around 400 to 770, except June at 1,704. Something happened to Network in June. Keep that in mind.
- **SLA attainment by priority:** P1 0.383, P5 0.894. The most urgent tickets miss their target most
  often. The targets for P1 are the tightest (`docs\sla.md`), so this is partly arithmetic; the
  question for the desk is whether 38% is acceptable for the tickets that matter most.
- **Category Pareto:** Inquiry / Help plus Network is half of all tickets (cumulative 0.502). Three
  categories are 68%.
- **Backlog aging:** of the 150 open tickets, 62 had waited four to seven days when the snapshot was
  taken and 23 more than a week.

Open `src\agent\analytics\kpi.py` and find the function behind each table. Each is a `groupby` and one
aggregate; none is longer than six lines. Then open `src\agent\workflow\routing.py`: `routing_table`
counts closed incidents per category and group and keeps the biggest group per category; `ROUTES` is the
result, written into the file; a test checks they still agree. On this corpus every category went to one
group, which is why `routing_accuracy` has been 1.0. Write in your journal what a real desk's table would
look like and what the harness number would then measure.

Five observations in your journal, each citing a number, at least one about Network in June.

## Part 2: the question and the method (10 min)

Open `src\agent\analytics\change_impact.py` and read the module docstring, then the functions in order:

- `incidents_in_window(history, start, hours, category)`: the rows opened in `[start, start + hours)`,
  optionally one category.
- `observed_count`: how many of those.
- `expected_count`: yours (Part 3).
- `surprise`: slides a window of the same length across the baseline, one start per day, and reports the
  share that held at least `observed` tickets.
- `impact_table`: one row per change with observed, expected, ratio and surprise over all categories,
  then the same for the single category with the largest ratio. Sorted by ratio.

Three decisions are built in, and each is a question you should be able to argue:

1. **The window starts at `end`, not `start`.** A change cannot cause incidents before it is made. (You
   will try `start` in Part 4 and see it barely matters here; it matters when windows are long.)
2. **The baseline is the 28 days before the change,** not the whole history: volume trends upward across
   the six months, so March is a poor estimate of normal for an August change.
3. **The comparison is per category as well as overall.** A change to a switch should show in Network
   and nowhere else; a lift confined to one category is far more believable than a small lift everywhere.

## Part 3: write the baseline (15 min)

Find `def expected_count`. Replace the whole function with:

```python
def expected_count(history: pd.DataFrame, change_end: pd.Timestamp, hours: int = WINDOW_HOURS,
                   baseline_days: int = BASELINE_DAYS, category: str | None = None) -> float:
    """The number of incidents a window of `hours` would normally hold: the baseline rate times the window."""
    start = change_end - pd.Timedelta(days=baseline_days)
    before = history[(history["opened_at"] >= start) & (history["opened_at"] < change_end)]
    if category is not None:
        before = before[before["category"] == category]
    per_hour = len(before) / (baseline_days * 24)
    return per_hour * hours
```

Line by line: `start` is 28 days before the change ended; `before` keeps the rows opened in that span
(the two conditions in parentheses joined by `&` are pandas for "both"); the category filter is applied
only when one is asked for; `per_hour` is the baseline's tickets divided by its hours; the result is that
rate times the window's hours. With 28 days and a 72-hour window this is the baseline count times
72 / 672, roughly one ninth.

```
python -m pytest tests\test_change_impact.py -v
```

Expected: four `PASSED`, no skips. The test builds a toy history of ten tickets a day with a burst of
forty after one change and checks your function returns 30.0 for the 72-hour window (10 a day times
three days) and 24.0 for Network alone.

## Part 4: run it and read it (20 min)

```
python -m agent.analytics.change_impact
```

Expected: a table with six rows, sorted by ratio, with these columns: `number`, `cmdb_ci`, `end`,
`observed`, `expected`, `ratio`, `surprise`, `top_category`, `top_observed`, `top_expected`, `top_ratio`,
`top_surprise`, and a last line starting `largest lift:`. The first row has a ratio of about 2.5 and a
surprise of 0.000, and its top category has a ratio above 7 on a hundred tickets. The other five have
ratios between 1.1 and 1.5. Copy the table into your journal.

Now read it against three traps.

**Trap 1: ratio without count.** Look down `top_ratio`. One decoy shows a top-category ratio of about 3
with a surprise of 0.000, which looks like a finding. Look at `top_observed` and `top_expected` for that
row: thirteen tickets against four. Four expected tickets means the baseline had about forty in 28 days
for that category, so a quiet month followed by an ordinary week produces a ratio of 3 by itself. The
first row's category has a hundred observed against thirteen expected. Report ratios together with the
counts they are made of; a ratio on single digits is a hint, not a finding.

**Trap 2: the window.** Run two variants and compare the first row and the order of the rest:

```
python -m agent.analytics.change_impact --hours 48
```

The first row stays first with a similar ratio (its incidents came mostly in the first two days). The
decoys move around: with a shorter window and smaller counts, their ratios are noisier. A finding that
survives a change of window is one you can defend; one that appears only at one setting is not.

**Trap 3: one source of evidence.** Counts can be coincidence. The desk's own words are a second source.
Paste as one command:

```
python -c "
from agent.analytics.features import load_history
h = load_history()
hit = h[h['close_notes'].str.contains('CHG0030012', na=False)]
print(len(hit), 'close notes name the change')
print(hit['close_notes'].value_counts().head(3).to_string())
"
```

Replace `CHG0030012` with the number in your first row if it differs. Expected: two dozen close notes
name the change, all with the same story. Then widen it:

```
python -c "
import pandas as pd
from agent.analytics.change_impact import incidents_in_window, load_changes, load_history
h, c = load_history(), load_changes()
top = c[c['number'] == 'CHG0030012'].iloc[0]
w = incidents_in_window(h, top['end'], 72, 'Network')
print(len(w), 'Network tickets in the window;', int(w['close_notes'].str.contains('firmware|rollback|Building C', case=False).sum()), 'mention the firmware, a rollback or Building C')
print(w['subcategory'].value_counts().to_dict())
print('made SLA in window', round(w['made_sla'].mean(), 2), '; Network overall', round(h[h['category'] == 'Network']['made_sla'].mean(), 2))
print('median resolve minutes in window', w['resolve_minutes'].median(), '; Network overall', h[h['category'] == 'Network']['resolve_minutes'].median())
"
```

Expected: 100 Network tickets, 85 of them with the story in their close notes; three subcategories
sharing them; SLA attainment in the window less than half the usual; median resolve time five times
the usual. That last pair is the June Network number from Part 1, explained. One change, three kinds of
evidence: the count against the baseline, the category it is confined to, the words in the close notes.

Last: the change record says `close_code = successful`. Write one sentence in your journal on what the
post-implementation review should have said.

## Part 5: the picture and the memo (10 min)

```
python -m agent.analytics.change_impact --plot
```

Expected: the table again and `plot: ...\eval\reports\change_impact.png`. Open the file. Daily volume
for six months with every change's end as a dotted line and the first row's 72-hour window shaded. The Monday
peaks are the sawtooth; the shaded window is the one spike that is not a Monday.

Create `docs\memos\2026-10-22-a3-change-impact.md`, one page, for the change manager. Four headings:
**Finding** (the change, the counts, the ratio, one sentence of evidence from the close notes), **How
it was measured** (window, baseline, surprise, in words a manager can repeat), **What it means for
change management** (the review was wrong; what the record should say; what to check 72 hours after
every change from now on), **Limits** (the five decoys and why a ratio of 1.4 on seventy tickets is not a
finding; what a real desk would add: a control group of weeks with no change). No code, no library names,
every claim tied to a number in the table. The memo is graded as part of A3 next session; today it is a
draft.

## Deliverable (5 min)

1. Create `docs\journal\module-08a.md`:

   ```markdown
   # Module 8, session 1: KPIs and change impact

   ## KPIs
   <five observations, each with a number; the real-desk routing paragraph>

   ## The method
   <the three built-in decisions, in your words>

   ## The table
   <the change-impact table; the 48-hour variant's first row>

   ## Evidence
   <the close-notes counts; the SLA and resolve-time comparison; the sentence on the review>

   ## Help I used
   <one or two lines>
   ```

2. Save the snapshot:

   ```
   git status
   git add src\agent\analytics\change_impact.py docs\memos\2026-10-22-a3-change-impact.md docs\journal\module-08a.md
   git status
   git commit -m "A3: change-impact baseline and table; memo draft"
   git log --oneline -4
   ```

   > **Mac:** forward slashes in the `git add` line.

   `git status` must not list `eval\reports` (the plot is git-ignored) or `.env`. The commit prints
   `3 files changed`.

## What is next

Session 2 finishes A3: the governance document goes from skeleton to v1, trained models are put under
the same change discipline as writes, the harness gate is turned on, and the branch is tagged `v0.3`.

## Check yourself

1. Why 28 days rather than 30? (Four whole weeks: every weekday appears exactly four times, so the Monday
   peak and the weekend trough cancel in the average. Thirty days would over- or under-count one weekday.)
2. A change ends on a Friday evening. What does the 72-hour window contain, and what does that do to the
   ratio? (Saturday, Sunday, Monday: two quiet days and one peak. The baseline per-hour rate is a weekly
   average, so the expected count is about right on balance, but a one-day window would be wrong either
   way. That is a reason to prefer windows that are a multiple of a day and, better, a baseline of the
   same weekdays.)
3. The surprise column is 0.000 for the first row. What exactly was compared? (Each of the 25 three-day
   windows inside the 28-day baseline, starting at the same clock time on successive days, against the
   observed count; none reached it.)
4. Name the three kinds of evidence and say which one a model could have produced on its own. (The count
   against the baseline, the category concentration, the close-notes text. The first two come from
   `groupby`; the third is retrieval, which is what `find_similar_incidents` does.)
