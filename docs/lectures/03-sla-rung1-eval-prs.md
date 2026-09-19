# Module 3: Service Level Agreements, the first real classifier, ground truth, and pull requests

Delivered Thursday, Sep 17. Rewritten Sep 19 as a complete walkthrough. Prerequisite: the Rung 0 close-out
([Module 2 lecture](02-rung0-closeout.md)) is done and merged. Checklist and rubric:
[handout](../exercises/2026-09-17-first-classifier.md).

## What you will be able to do afterwards

1. Say what a Service Level Agreement promises, how ServiceNow turns impact and urgency into a priority, and
   what the agent may and may not say to a customer about either.
2. Explain the difference between a **prediction** (category, from text, by a model) and a **rule** (priority,
   from two fields, by a lookup), and why the agent must never confuse them.
3. Train a text classifier on 3,461 closed incidents, test it on 781 later ones, and read its report.
4. Score the agent on the 40 held-out tickets with the eval harness and explain every line of the output.
5. Ship the work as a pull request with an Architecture Decision Record and a model card.

## Why this session exists

**The capability thread.** Rung 1 is "ticket classification plus priority versus SLA rules, with an eval
harness". Today you build the first classifier and the priority rule, and you run the harness for real. The
rung ends at A1 on Sep 24 with tag `v0.1`.

**The analytics thread.** This is the first model of the course. A1 is a **bake-off**: four ways of
classifying a ticket, scored on the same 40 tickets, compared on accuracy, per-class F1, cost and latency, with
a memo recommending one. Today's model is row 1 (rules were row 0). Next week adds gradient boosting and an
LLM. Everything the later modules do, breach-risk scoring in A4, drift detection in A6, uses the same shape:
split by time, train, evaluate on held-out data, record the model as an artifact with a card.

**The version thread.** The first decision that deserves a written record is made today (how to split the
data), so today's PR carries the first ADR you write, and the first model artifact the repo will ever hold.

## Words you need

- **SLA (Service Level Agreement)**: a promise, per priority, of how fast the desk responds and resolves.
- **Impact** (1 wide, 3 one user) and **urgency** (1 high, 3 low): two fields the desk sets on every ticket.
- **Priority** (1 highest, 5 lowest): computed from impact and urgency by a fixed table. Never typed in.
- **Classifier**: a function from a ticket's text to one of six categories.
- **Training set / test set**: rows the model learns from, and rows kept back to measure it honestly.
- **Time-based split**: the test set is *later* than the training set, so the measurement resembles real use.
- **Precision** (of the tickets the model called Network, the share that really were), **recall** (of the
  real Network tickets, the share the model found), **F1** (their harmonic mean, one number per class).
- **Macro F1**: the average of the six per-class F1 scores, so a small class counts as much as a big one.
- **Confusion matrix**: a table with true categories as rows and predicted categories as columns. The
  diagonal is right; everything else is a specific kind of wrong.
- **Holdout / eval set**: the 40 open tickets your seeder set aside. Nothing is ever tuned on them.
- **Model artifact**: the trained model saved to a file (`.joblib`). **Model card**: the JSON next to it
  saying what data, what split, what scores, what version, which ADR.
- **ADR (Architecture Decision Record)**: a one-page document saying what was decided, why, and what else
  was considered. Numbered, kept in `docs/adr/`, merged with the code it governs.

## Before you start

```
git checkout main
git pull origin main
pytest -q
ls data/eval/eval_set.jsonl
```

Expected: pytest ends with `passed` and some `skipped` (the skips are today's work); the last command prints
the path (the seeder wrote it in Module 2). If it says no such file, run `python scripts/seed_pdi.py` after
`python scripts/reset_pdi.py`.

## Part 1: Service Level Agreements and customer communication (15 min)

### What an SLA is

A Service Level Agreement is a promise with a clock. For incidents it has two clocks per priority:

- **Response target**: time until someone acknowledges the ticket.
- **Resolution target**: time until the service is restored.

Priority is not chosen by the caller and not chosen by a model. It is looked up:

| | Urgency 1 (high) | Urgency 2 | Urgency 3 (low) |
|---|---|---|---|
| **Impact 1 (wide)** | P1 | P2 | P3 |
| **Impact 2** | P2 | P3 | P4 |
| **Impact 3 (one user)** | P3 | P4 | P5 |

In the repo this table is `PRIORITY_MATRIX` in `src/agent/workflow/sla.py` and the function
`priority(impact, urgency)` reads it. It is the **only** code allowed to produce a priority. Open the file
now and find both. Below them is `TARGETS_MIN`: for each priority, `(response minutes, resolution minutes)`.
The values there are placeholders marked `TODO(student, Module 3)`.

### Step 1: write your one-page SLA

Create `docs/sla.md`. One page, four parts:

1. **A table** with five rows (P1 to P5) and two columns (response target, resolution target), in minutes.
   The corpus you analysed on Tuesday was generated against resolution targets of 240, 480, 1440, 2880 and
   7200 minutes for P1 to P5 (four hours to five days). Start from those unless you can argue for others;
   if you change them, the breach rates you computed change meaning.
2. **The clock rule**: does the clock run around the calendar or only in business hours (say 8 to 18,
   Monday to Friday)? Write one sentence. A four-hour P1 target that runs over a weekend is a breach
   schedule, not a target.
3. **Pause conditions**: the clock stops while the desk is waiting on the customer. One sentence.
4. **Communication moments**: see the table in the next section; copy it and fill in who writes each message.

### Step 2: put the targets in the code

In `src/agent/workflow/sla.py`, replace the `TARGETS_MIN` values with your table, response first,
resolution second, all in minutes. Keep the shape:

```python
TARGETS_MIN = {1: (15, 240), 2: (30, 480), 3: (60, 1440), 4: (240, 2880), 5: (480, 7200)}
```

Run `pytest tests/test_sla.py`. Both tests must still pass: the matrix corners, and the timer, which
already knows how to start, pause, resume and breach (Module 10 wires it to live tickets).

### What the breach numbers say

Put Tuesday's table on the screen:

| Priority | Tickets | Breach rate |
|---|---|---|
| 1 | 266 | 0.617 |
| 2 | 300 | 0.493 |
| 3 | 463 | 0.363 |
| 4 | 1,224 | 0.301 |
| 5 | 1,989 | 0.106 |

P1 breaches six times in ten. Three explanations fit: the P1 target is too tight; the desk is understaffed
for P1 work; too many tickets are being marked impact 1 urgency 1. This table cannot tell them apart. A2
asks you to compute what can: resolve time against target, by priority and by month, and who is setting
impact and urgency.

### Customer communication

| Moment | Message | Who writes it |
|---|---|---|
| Ticket opened | Acknowledgement with ticket number and the response target | A template; the system fills in fields |
| Approaching breach | Status update with a revised estimate | A template, triggered by the timer |
| Resolved | Resolution notice and a request to confirm | A template |
| Breached | Apology, what happened, what will change | A person |

Two rules the agent follows from today, on top of section 5 of `docs/governance/governance.md`:

- **Never present a prediction as a fact.** A classifier says "Network, 0.62". Customer-facing text says
  either what the desk decided or nothing about category.
- **Never let a model touch the clock.** Targets, elapsed time and breach are computed from timestamps and
  the matrix. A model that decides a ticket "is not really urgent" has rewritten a contract.

## Part 2: a prediction is not a rule (10 min)

| | Category | Priority |
|---|---|---|
| Input | Free text | Two integers the desk recorded |
| How | A model predicts | A table lookup |
| Can be wrong? | Yes, routinely | Only if the code is wrong |
| Needs a confidence? | Yes | No |
| Who may do it | Any model, audited | `sla.priority()` only |

The course principle is **deterministic computation, LLM interpretation**: a model never computes a number
and never is the analytical model. The harness enforces this with `priority_sla_agreement`: the share of
eval tickets where the agent's reported priority equals the matrix result. Its threshold is 0.90 because
there is no excuse for less. Rung 0 scored 0.0 on it because the rules never set a priority.

### Step 3: make the agent report the priority

Open `eval/harness.py` and find `run_rung`. The rung 1 branch reads:

```python
    if rung == "1":
        from agent.analytics.predict import classify  # noqa: E402
        return [{**r, **classify(r)} for r in rows]
```

Change it to:

```python
    if rung == "1":
        from agent.analytics.predict import classify  # noqa: E402
        from agent.workflow.sla import priority  # noqa: E402
        return [{**r, **classify(r), "pred_priority": priority(int(r["impact"]), int(r["urgency"]))} for r in rows]
```

What it does: for each eval ticket `r`, keep everything in it, add the classifier's output, and add
`pred_priority` computed by the rule from the ticket's own impact and urgency. The eval set carries those two
fields (the harness joins them in from `incidents_open.csv`). That is the whole of "priority versus SLA
rules" at Rung 1: the agent calls the rule and never guesses. You cannot run this yet; there is no model.
Part 3 makes one.

## Part 3: the first real classifier (35 min)

### What TF-IDF does

A model cannot read. It needs numbers. TF-IDF turns a ticket into a row of numbers, one per word (and per
two-word phrase) in the vocabulary. Take two tickets:

- A: "vpn drops at home"
- B: "printer jams again at home"

The vocabulary is every word seen in training, about 5,400 words and phrases for this corpus. Ticket A gets a
non-zero number in the columns `vpn`, `drops`, `at`, `home`, `vpn drops`, and so on; ticket B in `printer`,
`jams`, `again`, `at`, `home`. The number is the **term frequency** (how often the word is in this ticket)
scaled down by how common the word is across all tickets (the **inverse document frequency**). `at` and
`home` appear in thousands of tickets, so they are worth little; `vpn` appears in a few hundred, so it is
worth a lot. `min_df=2` drops words seen in only one training ticket (typos, mostly); `sublinear_tf=True`
uses the logarithm of the count so a word repeated five times is not worth five times as much;
`ngram_range=(1, 2)` includes two-word phrases so that "not working" is a feature, not two.

### What logistic regression does

For each category it learns one weight per column. A ticket's score for Network is the sum of the weights of
the words it contains; the scores for the six categories are turned into probabilities that add to one; the
highest wins. That is all. `class_weight="balanced"` makes the model count a Database ticket (6 percent of
the data) as heavily as an Inquiry ticket (29 percent), so it does not learn to ignore small classes.
`max_iter=1000` gives the fitting procedure enough steps to settle.

### Why the split is by time

You could shuffle the 4,242 rows and keep 20 percent for testing. Do not. The corpus contains families of
tickets that paraphrase the same incident; shuffling puts siblings on both sides, and the model looks better
than it is. Also, August is where the data has changed (volume rose, Hardware got slow); a model that will
score September tickets should be tested on the latest month it has never seen. So: train on March to July
(3,461 rows), test on August (781 rows). `features.time_split` already does this with `cutoff="2026-08-01"`.

### Step 4: write ADR-0003

This split is a decision, and the ADR number goes into the model card, so the ADR comes first. Copy the
template and fill in every section:

```
cp docs/adr/0000-template.md docs/adr/0003-time-based-split.md
```

A complete example of what goes in it (use your own words, keep every heading):

```markdown
# ADR-0003: Time-based train/test split for the category classifier
- **Status:** Accepted
- **Date:** 2026-09-17
- **Rung/Module:** Rung 1 / Module 3
- **Related Issue/PR:** #<your PR number, fill in after opening it>

## Context
The classifier is trained on data/eval/incidents_history.csv (4,242 closed incidents, March to August 2026)
and will score tickets that arrive after it was trained. The corpus contains paraphrase families of the same
incident, and August differs from earlier months (volume trend, slow Hardware resolutions).

## Decision
Train on tickets opened before 2026-08-01 (3,461 rows) and test on August (781 rows). The first model is
TF-IDF (1-2 grams, min_df 2, sublinear TF) into logistic regression with balanced class weights, saved as
category-v0.1 with a model card naming this ADR.

## Alternatives considered
- Random 80/20 split: puts paraphrases of the same incident on both sides; the score would overstate
  performance on unseen incidents.
- K-fold cross-validation: same leak, and no single "later" test month to report.

## Consequences
The August test month is smaller than a random 20 percent would be (781 rows). Every later model in the
bake-off uses the same split so the rows are comparable. When September data exists, the cutoff moves.

## Action-tier impact
None. Model inference is read tier.
```

### Step 5: implement the pipeline

Open `src/agent/analytics/train.py`. `build_pipeline(kind)` raises `NotImplementedError`. Replace the
function body (keep the docstring) with:

```python
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    if kind not in PIPELINES:
        raise ValueError(f"unknown pipeline {kind!r}; choose from {PIPELINES}")
    tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    if kind == "lr":
        return make_pipeline(tfidf, LogisticRegression(max_iter=1000, class_weight="balanced"))
    raise NotImplementedError("gbm: Module 4")
```

`make_pipeline` chains the two steps so that `fit` runs TF-IDF then the regression, and `predict` does the
same in order. Everything around this function (the split, the evaluation, the card, the file writing) is
already written and tested. Run `pytest tests/test_analytics.py -v`: the `lr` pipeline test now passes
instead of skipping; the `gbm` one still skips.

### Step 6: train

```
python -m agent.analytics.train --version 0.1 --adr ADR-0003
```

Expected output:

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
saved src/agent/models/category-v0.1.joblib (0.4 MB) and category-v0.1.json
```

Read the table this way. `n` is how many August tickets have that true category. Precision, recall and F1
are per class, as defined above. The confusion matrix has the truth down the side and the prediction along
the top; a number off the diagonal is a specific mistake (the row's true class was predicted as the column's
class). On this synthetic corpus the score is perfect or nearly so, because the text of each subcategory was
generated from its own bank of phrases, and a bag of words separates banks exactly. On a real desk, where
agents type whatever they like, expect 0.7 to 0.85 and a confusion matrix worth an hour of reading. The
handout asks you to explain the perfect score; that explanation is the real deliverable of this step.

### Step 7: read the model card

Open `src/agent/models/category-v0.1.json`. Every field is something a reviewer six weeks from now will
ask for: `training_data.sha256` (which exact file trained it), `training_data.split`, `metrics`, `adr`,
`environment` (library versions), `pipeline` (the exact steps and settings). The artifact is 0.4 MB, well
under the "few MB" limit in COURSE_CONTEXT, so both files are committed. A model without a card is not
allowed in this repo.

## Part 4: score the agent (10 min)

```
python -m eval.harness --rung 1 --report eval/reports/rung1.json
```

Expected:

```
| Metric | Value |
|---|---|
| n | 40 |
| classification_accuracy | 1.0 |
| priority_sla_agreement | 1.0 |
| routing_accuracy | 0.0 |
| harmful_action_count | 0 |

- FAIL routing_accuracy: 0.0 vs threshold 0.75
```

Line by line: 40 held-out tickets; every category right; every priority equals the matrix (because of your
Step 3 edit; without it this line reads 0.0); routing is 0.0 because Rung 1 does not predict an assignment
group, and that metric is gated from A2, so the FAIL line is expected until then; no writes happened, so no
harmful actions. The exit code is 1 because of the routing line; that is fine today and the instructor knows.

Then the comparison the memo will be built from:

```
python scripts/bakeoff.py --rows rules,model:0.1
```

Expected: two rows. `rules` around 0.15 with most tickets unclassified; `model:0.1` at 1.0, about 20
milliseconds per prediction including the first load of the model, zero cost. Next week adds two more rows.

## Part 5: the pull request (10 min)

```
git checkout -b feature/rung1-baseline
git add docs/sla.md src/agent/workflow/sla.py docs/adr/0003-time-based-split.md \
        src/agent/analytics/train.py eval/harness.py \
        src/agent/models/category-v0.1.joblib src/agent/models/category-v0.1.json
git status
```

`git status` must not show `.env`, `eval_set.jsonl`, `ground_truth.csv`, or `eval/reports/`. Then:

```
git commit -m "Rung 1: SLA targets, time-based split (ADR-0003), TF-IDF+LR category model v0.1"
git push -u origin feature/rung1-baseline
```

Open the PR from the link. Fill the template: Rung 1; what changed (five things: SLA document and targets,
ADR-0003, the pipeline, the harness priority line, the model v0.1 with card); the harness table from Part 4
in "Eval results", with the Rung 0 numbers in the "Before" column; "ADRs touched: ADR-0003"; the checklist;
the disclosure. In the description also answer the handout's question about the confusion matrix or the
perfect score. Go back to `docs/adr/0003-time-based-split.md`, fill in the PR number, commit and push again.

No tag today. `v0.1` comes with the full A1 PR on Sep 24.

## Check yourself

1. A caller writes "this is urgent, make it a P1" in the description. What changes? (Nothing. Urgency is
   the desk's assessment, priority is the matrix, and text in a ticket is data, not an instruction.)
2. The model says "Security, 0.51" for a ticket whose truth is "Software". Which metric moves, and by how
   much on 40 tickets? (`classification_accuracy` falls by 1/40 = 0.025. Nothing else.)
3. Why is `priority_sla_agreement` 0.0 without the Step 3 edit and 1.0 with it? (Without it the agent
   reports no priority; with it, it calls the rule, which is by definition what the metric checks.)
4. Why can a random split make a model look better than it is? (Paraphrases of the same incident land in
   both training and test; the model recognises its siblings rather than generalising.)
5. Name three fields of the model card and who needs each.

## Instructor notes

- Timing: 15 + 10 + 35 + 10 + 10 = 80 minutes with the handout folded in. Part 1 step 1 (the one-page SLA)
  can be assigned as homework to bring the session under 75.
- The corpus is separable by a bag of words, so Step 6 scores 1.0. The lecture treats that as a finding
  about the data. If the corpus is hardened later, only the expected output blocks change.
- The harness exits 1 at Rung 1 because `routing_accuracy` is gated from A2 but checked now. That is a
  harness design choice to make explicitly (gate metrics by rung, or accept the red exit until A2).
