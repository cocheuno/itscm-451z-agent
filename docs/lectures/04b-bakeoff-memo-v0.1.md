# Module 4, session 2: the build review, the memo, and Rung 1 done

Before this lecture: session 1 is committed on your `module-04` branch with your own v0.2 and the bake-off
table in your journal. About 45 minutes of guided work, then the memo and the tag. Commands are for
Windows; a **Mac:** box follows where a command differs.

## What you will be able to do afterwards

1. Turn a comparison table into a one-page recommendation a service-desk manager can act on.
2. Reason about cost and speed at the desk's real volume rather than per prediction.
3. Pin the chosen model in configuration and prove the program uses it.
4. Walk through a build with someone else and say whether it is ready.
5. Tag a finished rung.

## Why this session exists

**Analytics.** A model that is never chosen is an experiment. A1 ends with a **model-selection memo**: the
document by which an analyst tells a manager which of four options to run and why. Writing it forces the
four axes into one decision. The same memo shape recurs in every later assignment: KPIs in A2, model
governance in A3, breach risk in A4. Learning to write one page that a manager trusts is the most
transferable skill in this course.

**Version management.** Rung 1 ends today. Your branch gets tag `v0.1`, the label that says "this is the
commit where Rung 1 was finished". The instructor's `main` gets the same tag and a GitHub release page with
the eval report attached; that page is what a grader opens first.

## Words you need

- **Memo:** one page, one decision, written for someone who will not read the code.
- **Build review:** a walk through what exists, out loud, with the terminal open. Not a presentation.
- **Pin:** fixing a choice in a configuration file so it does not change by accident.
- **Tag:** a permanent label on one commit. `v0.1` is Rung 1.
- **Release:** GitHub's page for a tag, with notes and attached files. The instructor publishes it.

## Before you start

On your `module-04` branch:

```
git status
python -c "from agent.analytics import predict; print(predict.versions(), predict.selected_version())"
```

Expected: `git status` reports nothing to commit (session 1 is saved), and the second line prints
`['0.1', '0.2'] 0.2`. The program currently uses v0.2 because it is newest and nothing is pinned.

## Part 0: the build review (10 min)

Do this out loud with the instructor, in this order, terminal open:

1. `git log --oneline -8`: read your commits from `v0.0` up. Say what each one added.
2. `python -m pytest -q`: the number and the skips. Say what the skip is (the `list_all` acceptance test
   from Module 2 if you did not finish it; otherwise nothing).
3. `python -m eval.harness --rung 1`: the four metrics. Say which threshold each is against and why the
   routing line is red.
4. `dir src\agent\models`: two artifacts, two cards. Open one card and read its `adr`,
   `training_data.sha256` and `metrics` fields aloud.

   > **Mac:** `ls src/agent/models`
5. `dir docs\adr`: ADR-0003 to ADR-0005. Say the decision each records in one sentence.
6. `git diff main --stat`: the files your branch changed. Nothing that should not be there.

The review has three outcomes: ready to tag; ready after a named fix; not ready. Write the outcome in your
journal. A build that cannot be walked through in ten minutes is not reviewable, and that is a finding
about the build.

## Part 1: read the table (10 min)

Your bake-off table from session 1 is in `docs\journal\module-04a.md`. Four rows. Read them in this order:

1. **Unclassified.** A row that leaves tickets unclassified is not comparable on accuracy alone; a desk
   still has to route those tickets by hand. Count that as cost.
2. **Accuracy and macro F1 together.** If accuracy is high and macro F1 is lower, a small class is being
   missed. On this corpus the two local models sit at 1.0; the LLM row is where you see the gap, and the
   per-class table says which class.
3. **Latency.** Milliseconds for the local models, over a second for the LLM. Ask: is anything waiting on
   the answer?
4. **Cost per prediction**, then multiply.

## Part 2: cost at the desk's volume (10 min)

The history has 4,242 incidents over six months, about 700 a month, 8,400 a year. Fill in this table with
your numbers:

| Row | Cost per prediction | Per month (700) | Per year (8,400) | Latency |
|---|---|---|---|---|
| rules | 0 | 0 | 0 | 0 ms |
| model:0.1 | 0 | 0 | 0 | about 5 ms |
| model:0.2 | 0 | 0 | 0 | about 3 ms |
| llm | your figure | multiply by 700 | multiply by 8,400 | about 1 s |

With the instructor's figure of $0.0012 the LLM row is $0.86 a month and about $10 a year. Money is not
what separates these options.

Two costs that are not in the table and belong in the memo as sentences, not numbers: the local models
must be retrained when the desk's language drifts (A6 measures that), which is an analyst's afternoon a
quarter; the LLM needs a key, a vendor contract, and a rule about what ticket text may leave the building.

## Part 3: write the memo (20 min)

Create the folder and the file:

```
mkdir docs\memos
```

> **Mac:** `mkdir -p docs/memos`

Then create `docs\memos\2026-09-24-a1-model-selection.md` with exactly these headings (keep the file name
even though the date has moved; it is the name the course uses):

```markdown
# A1 memo: which classifier should the service desk run?

**To:** Service Desk manager · **From:** <you> · **Date:** <today> · **Decision needed by:** <a week out>

## Question
One sentence: which of four ways of categorising incoming tickets should the program use at Rung 1?

## Options compared
The bake-off table (paste it), then your cost-at-volume table from Part 2.

## Recommendation
One option, in one sentence. Then three sentences of why, each pointing at a column of the table.

## What would change this
Two sentences. Example: "On real desk text the per-class scores for Database and Security will fall
first; if either drops below 0.7 the LLM row should be re-run." Or: "If the desk moves to a chat
interface, the one-second latency becomes a cost."

## Risks and controls
Three bullets. The prediction is a suggestion, never customer-facing as fact (governance section 5).
Priority is never set by any model. The model in use is pinned by version and changed only with an ADR.

## Next step
Which version is pinned and which ADR records the choice.
```

Write it for a manager: no library names, no code, every claim tied to a number in the table. On this
table the honest recommendation is v0.1: it ties v0.2 on every accuracy column, is one tenth the size, and
the LLM row is both slower and less accurate. The LLM stays as the row to re-run on real text. If your
table says something else, follow your table and say why.

## Part 4: pin the choice (5 min)

The memo names a version. Make the program use it.

1. Create the ADR:

   ```
   copy docs\adr\0000-template.md docs\adr\0006-served-category-model.md
   ```

   > **Mac:** `cp docs/adr/0000-template.md docs/adr/0006-served-category-model.md`

   Fill every section, two or three sentences each. Decision: the program serves `category-v0.1`; the pin
   is `CATEGORY_MODEL_VERSION` in `.env`; changing it needs a new ADR and a memo. Alternatives: serve the
   newest automatically (rejected: a retrain would silently change behaviour). Action-tier impact: none.
2. In `.env`, set `CATEGORY_MODEL_VERSION=0.1`. In `.env.example`, keep the value empty but add a comment
   line above it: `# Current recommendation: 0.1 (ADR-0006, A1 memo)`.
3. Prove it:

   ```
   python -c "from agent.analytics import predict; print(predict.selected_version())"
   python -m eval.harness --rung 1 --report eval\reports\rung1.json
   ```

   The first prints `0.1`. The harness table is unchanged from Module 3 (v0.1 was already perfect) and goes
   in your journal.

## Part 5: the commit and the tag (10 min)

1. Create `docs\journal\module-04b.md`:

   ```markdown
   # Module 4, session 2: build review, memo, v0.1

   ## Build review outcome
   <ready / ready after fix / not ready, and the named fixes>

   ## Cost at volume
   <your table from Part 2>

   ## Recommendation
   <one sentence, the same as the memo>

   ## Harness table with the pin
   <paste>

   ## Help I used
   <one or two lines>
   ```

2. Save and tag:

   ```
   git status
   git add docs\memos\2026-09-24-a1-model-selection.md docs\adr\0006-served-category-model.md .env.example docs\journal\module-04b.md
   git status
   git commit -m "A1: model-selection memo, served model pinned (ADR-0006)"
   git tag -a v0.1 -m "Rung 1: category classifier bake-off, served model pinned"
   git log --oneline -3
   ```

   > **Mac:** forward slashes in the `git add` line.

   `git status` must not mention `.env` (only `.env.example`), `eval\reports`, or `logs`. The commit prints
   `4 files changed`. The log shows your commit on top with `(HEAD -> module-04, tag: v0.1)`.

That is Rung 1 finished. The instructor publishes the GitHub release for `v0.1` from `main` with the eval
reports attached; your branch and journal are what you walk through for the grade.

## What A1 is graded on

- The bake-off table with four rows, produced by the script, not typed.
- The memo: one decision, tied to the table, readable by a manager.
- ADR-0003 to ADR-0006 present and read; your own words on each in the journals.
- Two model artifacts with cards under `src\agent\models`, the served one pinned.
- Tag `v0.1` on your branch; the journals for both sessions.

## What is next

Module 5 starts Rung 2: the program reads. Sentence embeddings for "find similar incidents", the knowledge
base search tool, and the KPI functions (MTTR, SLA attainment by priority, backlog aging) computed from the
history. A2 is due Oct 8. The Monday volume and the Hardware column you noticed in Module 2 come back as
the first KPIs.

## Check yourself

1. Your table shows the LLM near 0.65 and the local models at 1.0. Which would you recommend for a desk
   whose real tickets are nothing like this corpus, and what would you ask for before deciding? (Neither,
   yet: a sample of real tickets with their categories, scored by all four rows.)
2. What breaks if someone trains `category-v0.3` and the pin is still `0.1`? (Nothing served changes,
   because the pin holds. Without the pin the program would silently switch models.)
3. Why does the release attach the report file rather than link to a page that can be edited? (The
   attached file is what the numbers were on the day.)
4. Name one number in your memo a manager could check without opening a terminal, and how. (The cost per
   year: price sheet times tokens times volume.)
