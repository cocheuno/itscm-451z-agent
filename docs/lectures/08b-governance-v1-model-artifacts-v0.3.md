# Module 8, session 2: governance v1, models as change-managed artifacts, and v0.3 (A3 due)

Before this lecture: session 1 is committed on `module-07` with the memo draft. About 60 minutes:
a build review, two documents, a gate, a tag. Commands are for Windows; a **Mac:** box follows where a
command differs.

## What you will be able to do afterwards

1. Write the governance document's first real version: scope, tiers, approval, audit, the never-do list,
   one responsible-use case, degraded modes.
2. Apply change management to a trained model: say what the change record, approval, rollback and
   post-implementation review are for a model version, and write that down as an ADR.
3. Explain what the CI gate checks from today and why `harmful_action_count` is the metric that matters.
4. Finish Rung 3 on your branch with tag `v0.3`.

## Where the repository already stands

| Item | On `main`? | What you do |
|---|---|---|
| `docs\governance\governance.md` skeleton with sections 2 and 3 from Module 7 | Your branch | Write sections 1, 4, 5, 6, 7 (Part 2) |
| Model cards (`src\agent\models\category-v0.1.json`, `v0.2.json`) and ADR-0003, 0004, 0006 | Yes | Read as change records (Part 3) |
| ADR-0008, models as change-managed artifacts | No | Write it (Part 3) |
| CI harness gating (`.github\workflows\eval.yml`) | Yes | Run the same command locally (Part 4) |

## Why this session exists

**ITSM.** Governance is change management written down for a system that acts on its own: what it is
for, what it may change, who approves, what is logged, what it must never do, what happens when it is
degraded. The skeleton has existed since Module 2. Today it becomes a document someone could hold the
program to.

**Version management.** `COURSE_CONTEXT.md` says models are change-managed artifacts. You have been
treating them that way without naming it: each version has a card with the training data's hash, an ADR
that says why it exists, a pin in `.env` that says which one is served, and a tag. Today you write the
mapping explicitly, so that retraining in Module 14 follows a rule rather than a habit.

**Analytics.** The gate. From today the CI harness fails a pull request whose numbers fall below
`eval\thresholds.yaml`, and the number that can only go one way is `harmful_action_count`. The analytics
half of A3 was session 1; today its memo is finished and reviewed.

## Words you need

- **Governance document:** the rules the agent runs under, kept in the repository and changed only by PR.
- **Scope of autonomy:** what the program is for and the tables it may touch; everything else is out.
- **Degraded mode:** a reduced behaviour the program falls back to when something fails: read-only,
  propose-only, human queue. The runbook (Module 9) says when; governance says which exist.
- **Model card:** the JSON next to each `.joblib`: version, training data hash, split, metrics, the ADR
  that justifies it, the environment it was trained in.
- **Gate:** a CI step that fails the build. Until today the harness step only reported.

## Before you start

```
git status
git log --oneline -4
python -m pytest -q
```

Expected: nothing to commit; three Module 7 and 8 commits on top of the instructor's; `passed` with
`1 skipped` (`list_all`).

## Part 1: build review (15 min)

With the terminal open, walk the instructor through Rung 3 in this order, saying what each thing is
before running it: the three write schemas and their tiers; `dispatch`, pointing at the branch that
refuses; the approvals command listing your proposals (`--all`); the audit entry for your live write and
its before-image; the rollback you ran; the change-impact table and the three kinds of evidence; the
memo draft. Outcome in the journal: ready, ready after a named fix, or not ready. Make the fixes now
(they are a commit on this branch like any other), then go on.

## Part 2: governance v1 (20 min)

Open `docs\governance\governance.md`. Sections 2 and 3 are done. Replace the one-line prompts in the other
sections with text. Two to five sentences each; concrete, naming files and commands; nothing the code
does not do.

- **1. Scope of autonomy.** What the program is for (triage of incidents in one PDI: classify, route,
  recommend; propose assignments, resolutions and comments). The tables it reads (`incident`, `sc_*`,
  `kb_knowledge`, `cmdb_ci`, `sys_user_group`, `change_request` from the CSV) and the one it writes
  (`incident`, three fields). What it is not for: anything customer-facing without the output filter,
  anything on change or problem records, anything outside the PDI.
- **4. Audit.** `logs\audit.jsonl`, one JSON line per action including refusals; the fields (ticket, tool,
  tier, inputs, reasoning, outcome, approval id, idempotency key, before-image, harmful). Retention: the
  file is per machine and never committed; the instructor holds the graded copies. Who may read it: the
  operator and the instructor.
- **5. What the agent must never do.** Start from the three given. Add from Modules 7 and 8: never execute
  a write without a valid approval for exactly those arguments; never reuse an approval; never write
  without a before-image; never post CMDB fields or retrieved text in a comment; never change its own
  tier, schema or governance; never run live without a named operator present. Each one should be
  traceable to a line of code or a test; say which.
- **6. Responsible use.** One concrete case, written out: the Building C change. After `CHG0030012`, a
  hundred Network tickets arrived in three days with the same cause. Under Rung 3 the program would
  propose `Network Ops` for each; under a future autonomous tier it would assign them. What should it
  do instead when the hundredth ticket looks like the first ninety-nine (recognise the pattern and
  raise a problem candidate, Rung 5; stop proposing and route to the human queue), and who decides.
- **7. Degraded modes.** List the three from the runbook with one sentence each on what the program may
  still do, and say that the runbook (Module 9) owns the triggers.

Bump the header line from `v0 skeleton` to `v1 (A3)`.

## Part 3: models as change-managed artifacts (10 min)

Open `src\agent\models\category-v0.1.json` and read the fields. Then fill this table in your journal:

| Change management | For a model version | Where it lives |
|---|---|---|
| Change record | | |
| Approval | | |
| Change window / deployment | | |
| Rollback plan | | |
| Post-implementation review | | |

Answers to check against: the card and its ADR are the record; the instructor's PR review is the
approval; deployment is the pin `CATEGORY_MODEL_VERSION` plus the release tag; rollback is setting the pin
back to the previous version, which is still on disk; review is the harness table and the bake-off.

Now write it down:

```
copy docs\adr\0000-template.md docs\adr\0008-models-are-change-managed.md
```

> **Mac:** `cp docs/adr/0000-template.md docs/adr/0008-models-are-change-managed.md`

Context: models change behaviour as surely as code; retraining on new data is a change to production.
Decision: every model version has a card, an ADR, a PR, a pin and a tag; retraining produces a new
version and never overwrites one; the served version changes only by editing the pin with an ADR and a
memo (ADR-0006 set the precedent); rollback is the pin. Alternatives: retrain in place (rejected: no
rollback); serve the newest automatically (rejected in ADR-0006). Consequences: artifacts accumulate
(the size rule keeps them small); Module 14's retraining trigger must produce a PR, not a file.
Action-tier impact: none; `classify_incident` stays `read`.

## Part 4: the gate (5 min)

The CI workflow runs exactly this; run it yourself:

```
python -m eval.harness --rung auto --fixtures --report eval\reports\local.json
python -m pytest -q
```

> **Mac:** `eval/reports/local.json`.

Expected: the rung 3 table (classification 1.0, priority 1.0, routing 1.0, harmful 0) and no `FAIL`
line; exit code zero. Open `eval\thresholds.yaml`: four numbers, each with the assignment that set it.
From today the harness step in `.github\workflows\eval.yml` no longer has `continue-on-error`, so a pull
request to the instructor's `main` fails if any number is below its threshold or a harmful action is
counted. `harmful_action_count` is the one to watch: accuracy can be argued about; a write without
approval cannot.

## Part 5: finish the memo, commit, tag (10 min)

Open `docs\memos\2026-10-22-a3-change-impact.md` and finish it from the build-review feedback. Then:

1. Create `docs\journal\module-08b.md`:

   ```markdown
   # Module 8, session 2: governance v1, model artifacts, v0.3

   ## Build review outcome
   <ready / ready after fix / not ready, and the named fixes>

   ## Governance
   <the never-do list, each item with the code or test it maps to>

   ## Models as artifacts
   <the filled-in table>

   ## The gate
   <the harness table; the four thresholds and what each gates>

   ## Help I used
   <one or two lines>
   ```

2. Save the snapshot and tag it:

   ```
   git status
   git add docs\governance\governance.md docs\adr\0008-models-are-change-managed.md docs\memos\2026-10-22-a3-change-impact.md docs\journal\module-08b.md
   git status
   git commit -m "A3: governance v1, models as change-managed artifacts (ADR-0008)"
   git tag -a v0.3 -m "Rung 3: writes under guardrails; change-impact analysis"
   git log --oneline -5
   ```

   > **Mac:** forward slashes in the `git add` line.

   `git status` must not list `.env`, `logs` or `eval\reports`. The commit prints `4 files changed`. The
   log's top line ends `(HEAD -> module-07, tag: v0.3)`.

That is Rung 3 finished. The instructor publishes the `v0.3` release from `main`; your branch and the four
journals are what you walk through for the grade.

## What A3 is graded on

- ADR-0007 with a decision and the condition that would change it; the governance table row agreeing.
- The before-image method and `rollback`, tests passing; the audit entries for one live write and its
  rollback, with the PDI history to match.
- `expected_count` written; the change-impact table in the journal; the finding defended with the
  count, the category and the text, and the decoys explained.
- The memo: one page, one finding, numbers from the table, a recommendation a change manager can act on.
- Governance v1 with every never-do item traceable to code or a test; ADR-0008.
- Tag `v0.3` on `module-07`; journals for all four sessions.

## What is next

Module 9 is business continuity: anomaly detection on daily ticket volume (the Building C spike is the
test case), wired to the agent-failure runbook so that an anomaly puts the program into a degraded mode.
Then Module 10 and A4: the request workflow with SLA timers and a breach-risk score.

## Check yourself

1. The harness reports `harmful_action_count 1` on a pull request. What are the four things that could
   have produced it? (A write executed above its tier, without a valid approval, against a missing target,
   or with a reused approval; `eval\metrics.py` lists them and `dispatch` sets the flag.)
2. A retrained `category-v0.3` scores higher than v0.1 on August. What has to happen before the program
   serves it? (A card, an ADR, a PR with the bake-off table, the pin changed with a memo, a tag. Nothing
   about the score alone changes the pin.)
3. Which governance section would a service-desk lead read first, and what should they find there?
   (Section 5. A short list of absolute rules, each one checkable.)
