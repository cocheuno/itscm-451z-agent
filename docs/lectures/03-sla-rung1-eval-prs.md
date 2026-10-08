# Module 3: Service Level Agreements, the first real classifier, and ground truth

Before this lecture: Module 2 is done on your `module-02` branch, and you have read
[Getting started](00-getting-started.md). Commands are for Windows; a **Mac:** box follows where a command
differs. Checklist and rubric: [handout](../exercises/2026-09-17-first-classifier.md).

## What you will be able to do afterwards

1. Say what a Service Level Agreement promises, how ServiceNow turns impact and urgency into a priority,
   and what the program may and may not say to a customer about either.
2. Explain the difference between a **prediction** (a category guessed from text by a model) and a
   **rule** (a priority looked up from two fields), and why the program must never confuse them.
3. Train a text classifier on 3,461 closed tickets, test it on 781 later ones, and read its report:
   precision, recall, F1, and a confusion matrix.
4. Score the program on the 40 held-out tickets with the eval harness and explain every line.
5. Read a model card and an Architecture Decision Record, and write your own SLA page.

## Where the repository already stands

The instructor has merged his own version of this module into `main`, so some of today's files already
exist in your fresh clone. Where that is the case, your job is to read, run, and explain, not to type the
same thing again. Where it is not, you write it.

| Item | On `main`? | What you do |
|---|---|---|
| `docs/sla.md`, the one-page SLA | No | Write it (Part 1) |
| `TARGETS_MIN` in `src/agent/workflow/sla.py` | Placeholder values with a `TODO` | Decide the numbers, remove the `TODO` (Part 1) |
| ADR-0003, the split decision | Yes, written by the instructor | Read it; explain the decision in your journal (Part 3) |
| `build_pipeline("lr")` in `train.py` | Yes | Read it line by line (Part 3) |
| The priority line in `eval/harness.py` | Yes | Read it (Part 2) |
| Model `category-v0.1` with its card | Yes, trained on the instructor's laptop | Train your own and compare the two cards (Part 3) |

## Why this session exists

**The capability thread.** Rung 1 is "sort tickets into categories with a trained model, set priority by
the rule, measure both". Today is the first model and the first honest measurement.

**The analytics thread.** This is the first model of the course, and the shape of it repeats in every
later assignment: split the data by time, train on the early part, test on the later part, report the
scores per class, save the model with a card that records exactly what it was built from. A1 next week is a
**bake-off**: four ways of categorising a ticket, scored on the same 40 tickets, compared on accuracy,
per-class scores, speed and cost, with a memo recommending one. Today's model is one of the four rows; the
keyword rules from Module 2 are another.

**The version thread.** The first decision that deserves a written record is how to split the data. It
lives in an ADR, and the model card names that ADR, so anyone opening the model later can find out why it
was built the way it was.

## Words you need

- **SLA (Service Level Agreement):** a promise, per priority, of how fast the desk responds and resolves.
- **Impact** (1 affects many, 3 affects one person) and **urgency** (1 high, 3 low): two fields the desk
  sets on every ticket.
- **Priority** (1 highest, 5 lowest): computed from impact and urgency by a fixed table. Never typed in.
- **Model:** a program whose behaviour was set by data rather than written by hand. Today's model reads a
  ticket's text and returns one of six categories.
- **Training set / test set:** the rows a model learns from, and the rows kept back to measure it. Scoring
  on the training rows is like grading an exam with the answers on the desk.
- **Time-based split:** the test rows are *later* than the training rows, so the measurement looks like
  real use, where the model always meets tickets newer than anything it learned from.
- **Precision:** of the tickets the model called Network, the share that really were Network. Low precision
  means false alarms.
- **Recall:** of the tickets that really were Network, the share the model caught. Low recall means misses.
- **F1:** one number per class that is high only when precision and recall are both high.
- **Macro F1:** the average of the six per-class F1 numbers, so a small class counts as much as a big one.
- **Confusion matrix:** a table with the true categories down the side and the predicted ones across the
  top. The diagonal is right; every other cell is one specific kind of mistake.
- **Holdout / eval set:** the 40 open tickets set aside in Module 2. Nothing is ever tuned on them.
- **Model artifact:** the trained model saved to a file (`.joblib`). **Model card:** the JSON file beside it
  that records the data, the split, the scores, the version, and the ADR.
- **ADR (Architecture Decision Record):** a one-page document saying what was decided, why, and what else
  was considered. Numbered, kept in `docs/adr/`.

## Before you start

```
git checkout main
git pull origin main
python -m pytest -q
git checkout -b module-03
dir data\synthetic\eval_set.jsonl
```

> **Mac:** `ls data/synthetic/eval_set.jsonl`

Expected: pytest ends `70 passed, 1 skipped` (or more passed; never fewer); the branch command prints
`Switched to a new branch 'module-03'`; the last command lists the file the seeder wrote in Module 2. If it
says the file cannot be found, the scoring program will use the committed copy at
`data\eval\eval_set.jsonl`, which has the same 40 tickets, so you can continue.

## Part 1: Service Level Agreements and customer communication (15 min)

### What an SLA is

A Service Level Agreement is a promise with a clock. For incidents there are two clocks per priority:

- **Response target:** time until someone acknowledges the ticket.
- **Resolution target:** time until the service is working again.

Priority is not chosen by the caller and never by a model. It is looked up:

| | Urgency 1 (high) | Urgency 2 | Urgency 3 (low) |
|---|---|---|---|
| **Impact 1 (many users)** | P1 | P2 | P3 |
| **Impact 2** | P2 | P3 | P4 |
| **Impact 3 (one user)** | P3 | P4 | P5 |

Open `src\agent\workflow\sla.py` in your editor. The table is `PRIORITY_MATRIX` near the top, and
`priority(impact, urgency)` is the function that reads it. It is the **only** code in the whole program
allowed to produce a priority. Below it is `TARGETS_MIN`: for each priority, `(response minutes,
resolution minutes)`, marked `TODO(student, Module 3)`.

### Step 1: write your one-page SLA

Create a new file `docs\sla.md`. One page, four parts:

1. **A table** with five rows (P1 to P5) and two columns (response target, resolution target), in minutes.
   The history you analysed in Module 2 was generated against resolution targets of 240, 480, 1440, 2880
   and 7200 minutes for P1 to P5 (four hours up to five days). Start from those. If you change them, say
   why, and note that the breach rates you computed in Module 2 then mean something different.
2. **The clock rule:** does the clock run around the calendar, or only in business hours (say 8 to 18,
   Monday to Friday)? One sentence. A four-hour P1 target that keeps running over a weekend is a breach
   schedule, not a target.
3. **Pause conditions:** the clock stops while the desk is waiting on the customer. One sentence.
4. **Communication moments:** copy the table from "Customer communication" below and fill in who writes
   each message.

### Step 2: put the targets in the code

In `src\agent\workflow\sla.py`, set `TARGETS_MIN` to your table, response first, resolution second, all in
minutes, and delete the `# TODO(student, Module 3)` line above it. If you kept the defaults, the line stays
exactly:

```python
TARGETS_MIN = {1: (15, 240), 2: (30, 480), 3: (60, 1440), 4: (240, 2880), 5: (480, 7200)}
```

Then:

```
python -m pytest tests\test_sla.py -v
```

Expected: every line ends `PASSED`. The tests check the matrix corners and a timer that already knows how to
start, pause, resume and breach; Module 10 wires it to live tickets.

### What the breach numbers from Module 2 say

| Priority | Tickets | Breach rate |
|---|---|---|
| 1 | 266 | 0.617 |
| 2 | 300 | 0.493 |
| 3 | 463 | 0.363 |
| 4 | 1,224 | 0.301 |
| 5 | 1,989 | 0.106 |

P1 misses its deadline six times in ten. Three explanations fit: the P1 target is too tight; the desk is
understaffed for P1 work; too many tickets are being marked impact 1 and urgency 1. This table cannot tell
them apart, and that is the normal situation in analytics: the first table raises the question, the next
table answers it. A2 asks for the next table: resolve time against target by priority and by month, and
who is setting impact and urgency.

### Customer communication

| Moment | Message | Who writes it |
|---|---|---|
| Ticket opened | Acknowledgement with ticket number and the response target | A template; the system fills in fields |
| Approaching breach | Status update with a revised estimate | A template, triggered by the timer |
| Resolved | Resolution notice and a request to confirm | A template |
| Breached | Apology, what happened, what will change | A person |

Two rules the program follows from today, on top of section 5 of `docs\governance\governance.md`:

- **Never present a prediction as a fact.** A classifier says "Network, 0.62". Customer-facing text says
  what the desk decided, or nothing about category.
- **Never let a model touch the clock.** Targets, elapsed time and breach come from timestamps and the
  matrix. A model that decides a ticket "is not really urgent" has rewritten a contract.

## Part 2: a prediction is not a rule (10 min)

| | Category | Priority |
|---|---|---|
| Input | Free text | Two numbers the desk recorded |
| How | A model predicts | A table lookup |
| Can be wrong? | Yes, routinely | Only if the code is wrong |
| Needs a confidence? | Yes | No |
| Who may do it | Any model, with an audit entry | `sla.priority()` only |

The course principle is **deterministic computation, LLM interpretation**: a model never computes a number
and never is the analysis. The scoring program checks this with `priority_sla_agreement`: the share of eval
tickets where the program's reported priority equals the matrix result. Its threshold is 0.90, because there
is no excuse for less. Rung 0 scored 0.0 on it because the rules never set a priority.

### Read the line that fixes it

Open `eval\harness.py` and find `def run_rung`. The rung 1 branch reads:

```python
    if rung == "1":
        from agent.analytics.predict import classify  # noqa: E402
        from agent.workflow.sla import priority  # noqa: E402
        return [{**r, **classify(r), "pred_priority": priority(int(r["impact"]), int(r["urgency"]))} for r in rows]
```

What it does, for each eval ticket `r`: keep everything in the ticket, add the classifier's answer, and add
`pred_priority` computed by the rule from the ticket's own impact and urgency. That is the whole of
"priority versus SLA rules" at Rung 1: the program calls the rule and never guesses. Nothing to change.

## Part 3: the first real classifier (35 min)

### What a model needs: numbers

A model cannot read. It needs numbers. **TF-IDF** turns each ticket into a row of numbers, one column per
word (and per two-word phrase) seen in the training tickets. Two tickets:

- A: "vpn drops at home"
- B: "printer jams again at home"

| | vpn | drops | printer | jams | again | at | home |
|---|---|---|---|---|---|---|---|
| A | high | high | 0 | 0 | 0 | low | low |
| B | 0 | 0 | high | high | high | low | low |

A number is high when the word is in this ticket *and* rare across all tickets. `at` and `home` appear in
thousands of tickets, so they are worth little; `vpn` appears in a few hundred, so it is worth a lot. For
this corpus the vocabulary is about 5,400 words and phrases, so each ticket becomes a row of 5,400 numbers,
nearly all zero. Three settings you will see in the code: `min_df=2` drops words seen in only one training
ticket (mostly typos); `sublinear_tf=True` uses the logarithm of a word's count so five repeats are not
worth five times as much; `ngram_range=(1, 2)` includes two-word phrases so that "not working" is one
feature, not two.

### What logistic regression does

For each of the six categories it learns one weight per column. A ticket's score for Network is the sum of
the weights of the words it contains; the six scores are turned into probabilities that add to one; the
highest wins. That is the whole model. `class_weight="balanced"` makes the model count a Database ticket
(6 percent of the data) as heavily as an Inquiry / Help ticket (29 percent), so it does not learn to ignore
small classes. Remember the category shares from Module 2: this is where that imbalance bites.

### Why the split is by time

You could shuffle the 4,242 rows and keep 20 percent for testing. Do not. The corpus contains families of
tickets that are paraphrases of the same incident; shuffling puts siblings on both sides, and the model
looks better than it is because it recognises relatives rather than learning categories. Also, August is
where the data changed (volume rose, Hardware got slow), and a model that will score September tickets
should be tested on the latest month it has never seen. So: train on March to July (3,461 rows), test on
August (781 rows). `features.time_split` does this with `cutoff="2026-08-01"`.

### Step 3: read ADR-0003

Open `docs\adr\0003-time-based-split.md`. The instructor wrote it. Read all five sections, then write
three sentences in your journal in your own words: what was decided, what the alternative was, and what
would have gone wrong with the alternative. Do not copy the file.

### Step 4: read the pipeline

Open `src\agent\analytics\train.py` and find `def build_pipeline`. The `lr` branch is two lines:

```python
    tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    if kind == "lr":
        return make_pipeline(tfidf, LogisticRegression(max_iter=1000, class_weight="balanced"))
```

`make_pipeline` chains the two steps so that training runs TF-IDF then the regression, and predicting does
the same in the same order. Everything else in the file (the split, the evaluation, the card, the file
writing) is plumbing. Match each setting to the explanation above; you will be asked about them.

### Step 5: train it yourself

```
python -m agent.analytics.train --version 0.1 --adr ADR-0003
```

Expected, in about ten seconds:

```
train 3461 rows (opened_at < 2026-08-01), test 781 rows
accuracy 1.0  macro F1 1.0
class            precision  recall      f1     n
Database             1.000   1.000   1.000    47
Hardware             1.000   1.000   1.000   131
Inquiry / Help       1.000   1.000   1.000   212
Network              1.000   1.000   1.000   188
Security             1.000   1.000   1.000    60
Software             1.000   1.000   1.000   143
confusion (rows = truth, columns = predicted):
                 Databas Hardwar Inquiry Network Securit Softwar
Database              47       0       0       0       0       0
...
saved src\agent\models\category-v0.1.joblib (0.3 MB) and category-v0.1.json
```

How to read it. `n` is how many August tickets truly have that category. Precision, recall and F1 are per
class, as defined in the words list. The confusion matrix has the truth down the side and the prediction
across the top; any number off the diagonal is one specific mistake: that row's true class was predicted as
that column's class.

A worked example of the three scores, so they are not just words. Suppose 100 tickets are truly Network,
the model calls 90 of them Network and misses 10, and it also calls 30 non-Network tickets Network by
mistake. Recall is 90 out of 100, 0.90. Precision is 90 out of the 120 it called Network, 0.75. F1 is the
balance of the two, 0.82. A model can push recall up by calling everything Network, which ruins precision;
F1 punishes that.

**Why the score is perfect.** On this synthetic corpus every subcategory's text was generated from its own
bank of phrases, and a bag of words separates banks exactly. That is a finding about the data, not about
the model. On a real desk, where agents type whatever they like, expect 0.7 to 0.85 and a confusion matrix
worth an hour of reading. Your journal says this in your own words; it is the real deliverable of this step.

### Step 6: compare the two cards

The command overwrote the instructor's `category-v0.1.json` with yours. See the difference:

```
git diff src\agent\models\category-v0.1.json
```

Lines starting `-` are the instructor's card, lines starting `+` are yours. Expected: `created` and the
`environment.python` line differ, `training_data.sha256`, `split`, `metrics` and `adr` are identical. Same
data, same recipe, same result, different laptop. That is what a model card is for: a reviewer six weeks
from now can check all of it without you. The `.joblib` file also changed, which `git status` shows; it is
the model itself, 0.3 MB, and it is committed with its card because a model without a card is not allowed
in this repository.

## Part 4: score the program (10 min)

```
python -m eval.harness --rung 1 --report eval\reports\rung1.json
```

Expected:

```
eval set: data\synthetic\eval_set.jsonl (40 tickets)
| Metric | Value |
|---|---|
| n | 40 |
| classification_accuracy | 1.0 |
| priority_sla_agreement | 1.0 |
| routing_accuracy | 0.0 |
| harmful_action_count | 0 |

- FAIL routing_accuracy: 0.0 vs threshold 0.75
```

Line by line: 40 held-out tickets; every category right; every priority equals the matrix (the line you
read in Part 2); routing is 0.0 because Rung 1 does not predict a team, and that metric is gated from A2,
so the FAIL line is expected until then; nothing was written anywhere, so no harmful actions. Copy the
table into your journal.

Then the first two rows of the bake-off:

```
python scripts\bakeoff.py --rows rules,model:0.1
```

Expected: two rows. `rules` around 0.15 with most tickets unclassified; `model:0.1` at 1.0, a few
milliseconds per prediction, zero cost. Next week adds two more rows. Copy this table too.

## Deliverable

Your branch, a journal page, one commit. No push.

1. Create `docs\journal\module-03.md`:

   ```markdown
   # Module 3: SLA, first classifier, ground truth

   ## SLA decisions
   <your five targets in one line, your clock rule, your pause rule>

   ## The split, in my words
   <three sentences from Part 3 Step 3>

   ## Why the score is perfect
   <three or four sentences from Part 3 Step 5>

   ## Harness table for --rung 1
   <paste>

   ## Bake-off, first two rows
   <paste>

   ## Help I used
   <one or two lines>
   ```

2. Save the snapshot:

   ```
   git status
   git add docs\sla.md src\agent\workflow\sla.py src\agent\models\category-v0.1.joblib src\agent\models\category-v0.1.json docs\journal\module-03.md
   git status
   git commit -m "Rung 1: SLA page and targets, retrained category-v0.1, journal"
   git log --oneline -3
   ```

   > **Mac:** forward slashes in the `git add` line.

   The first `git status` must not mention `.env`, `eval_set.jsonl`, `ground_truth.csv`, or anything under
   `eval\reports` or `logs`. The commit prints `5 files changed`. No tag today; `v0.1` comes with the A1
   work in Module 4.

## Check yourself

1. A caller writes "this is urgent, make it a P1" in the description. What changes? (Nothing. Urgency is
   the desk's assessment, priority is the matrix, and text in a ticket is data, not an instruction.)
2. The model says "Security, 0.51" for a ticket whose truth is "Software". Which metric moves, and by how
   much on 40 tickets? (`classification_accuracy` falls by 1 in 40, which is 0.025. Nothing else.)
3. Why can a random split make a model look better than it is? (Paraphrases of the same incident land in
   both training and test; the model recognises its siblings instead of learning categories.)
4. Precision 0.95 and recall 0.40 for Security: what is the model doing? (Rarely calling tickets Security,
   and usually right when it does, but missing most real Security tickets. A desk would want recall up.)
5. Name three fields of the model card and who needs each. (`training_data.sha256`, for anyone checking
   which file trained it; `metrics`, for the memo; `adr`, for the reviewer asking why.)
