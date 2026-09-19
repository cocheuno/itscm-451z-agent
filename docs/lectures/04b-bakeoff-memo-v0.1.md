# Module 4, session 2: build review and the first tagged release

Thursday, Sep 24. Syllabus: "build review; first tagged release". A1 is due today. Prerequisite: the session 1 PR (`feature/rung1-bakeoff-models`) is
merged. About 45 minutes of guided work, then the A1 PR and the tag.

## What you will be able to do afterwards

1. Turn a comparison table into a one-page recommendation a service-desk manager can act on.
2. Reason about cost and latency at the desk's real volume rather than per prediction.
3. Pin the chosen model as configuration and prove the agent serves it.
4. Tag a release, attach the eval report, and know what a grader will open first.

## Why this session exists

**Analytics.** A model that is never chosen is an experiment. A1 ends with a **model-selection memo**: the
document by which an analyst tells a manager which of four options to run and why. Writing it forces the
four axes into one decision. In every later assignment the same memo shape recurs: KPIs in A2, model
governance in A3, breach-risk in A4.

**Version management.** Rung 1 ends today. The merge of the A1 PR is tagged `v0.1`, and the tag gets a
GitHub release with the eval report attached. From now on `git log main` reads as the rung history, and
anyone can check out `v0.1` and reproduce today's numbers.

## Words you need

- **Memo**: one page, one decision, written for someone who will not read the code.
- **Tag**: a named, permanent pointer to one commit. `v0.1` is Rung 1.
- **Release**: GitHub's page for a tag, with notes and attached files. The eval report goes there.
- **Pin**: fixing a choice in configuration so it does not change by accident.

## Before you start

```
git checkout main
git pull origin main
python -c "from agent.analytics import predict; print(predict.versions(), predict.selected_version())"
```

Expected: `['0.1', '0.2'] 0.2`. The agent currently serves v0.2 because it is newest and nothing is pinned.

## Part 0: the build review (10 min)

A build review is a walk through what exists, not a presentation. Do it out loud with the instructor, in
this order, with the terminal and GitHub open:

1. `git log --oneline main | head -12`: read the merges since `v0.0`. Each is a PR; say what each one added.
2. `pytest -q`: the number and the skips. Say what each skip is.
3. `python -m eval.harness --rung 1`: the four metrics. Say which threshold each is against and why the
   routing line is red.
4. Open `src/agent/models/`: two artifacts, two cards. Read one card's `adr`, `training_data.sha256` and
   `metrics` fields aloud.
5. Open `docs/adr/`: ADR-0003 to ADR-0005. Say the decision each records in one sentence.
6. `git diff main --stat` on your open branch: nothing that should not be there.

The review has three possible outcomes: ready to tag; ready after a named fix; not ready. Write the outcome
and the named fixes in the A1 PR description. A build that cannot be walked through in ten minutes is not
reviewable, and that is a finding about the build.

## Part 1: read the table (10 min)

```
python scripts/bakeoff.py --report eval/reports/bakeoff.json
```

Four rows. Read them in this order:

1. **Unclassified.** A row that leaves tickets unclassified (rules) is not comparable on accuracy alone;
   a desk still has to route those tickets by hand. Count that as cost.
2. **Accuracy and macro F1 together.** If accuracy is high and macro F1 is lower, a small class is being
   missed. Look at the per-class table underneath to find which one. On this corpus the two models sit at
   or near 1.0; the LLM row is where you will see differences, and the three `gt_ambiguous` tickets in the
   holdout are where they concentrate.
3. **Latency.** Milliseconds for the local models, about a second for the LLM. Ask: is anything waiting on
   the answer? A poller that runs every five minutes does not care; a chat window does.
4. **Cost per prediction**, then multiply.

## Part 2: cost at the desk's volume (10 min)

The history has 4,242 incidents over six months, about 700 a month. Fill in this table with your numbers:

| Row | Cost per prediction | Per month (700) | Per year | Latency |
|---|---|---|---|---|
| rules | 0 | 0 | 0 | 0 ms |
| model:0.1 | 0 | 0 | 0 | ~20 ms |
| model:0.2 | 0 | 0 | 0 | ~3 ms |
| llm | your figure | ×700 | ×8,400 | ~1 s |

Two more costs that are not in the table and belong in the memo: the local models must be retrained when
the desk's language drifts (A6 measures that), which is an analyst's afternoon a quarter; the LLM needs a
key, a vendor contract, and a rule about what ticket text may leave the building. Write both down as
sentences, not numbers.

## Part 3: write the memo (20 min)

Create `docs/memos/2026-09-24-a1-model-selection.md`. One page. Use exactly these headings:

```markdown
# A1 memo: which classifier should the service desk run?

**To:** Service Desk manager · **From:** <you> · **Date:** 2026-09-24 · **Decision needed by:** Sep 30

## Question
One sentence: which of four ways of categorising incoming tickets should the agent use at Rung 1?

## Options compared
The bake-off table (paste it), then the cost-at-volume table from Part 2.

## Recommendation
One option, in one sentence. Then three sentences of why, each pointing at a column of the table.

## What would change this
Two sentences. Example: "On real desk text the per-class F1 for Database and Security will fall first;
if either drops below 0.7 the LLM row should be re-run." Or: "If the desk moves to a chat interface, the
one-second latency becomes a cost."

## Risks and controls
Three bullets. The prediction is a suggestion, never customer-facing as fact (governance section 5). Priority
is never set by any model. The served model is pinned by version and retrained only through a PR with an ADR.

## Next step
Which version is pinned, which ADR records the choice, and the tag.
```

Write it for a manager: no library names, no code, every claim tied to a number in the table. Because this
corpus is synthetic and separable, the honest recommendation is usually the cheapest model that ties on
accuracy, with the LLM kept as the row to re-run on real text. If your table says something else, follow
the table.

## Part 4: pin the choice (5 min)

The memo names a version. Make the agent serve it:

1. `docs/adr/0006-served-category-model.md`: Decision: the agent serves `category-v<chosen>`; the pin is
   `CATEGORY_MODEL_VERSION` in `.env`; changing it requires a new ADR and a memo. Two paragraphs are enough.
2. In `.env`, set `CATEGORY_MODEL_VERSION=0.1` (or `0.2`). In `.env.example`, leave it empty but add a
   comment naming the current recommendation and ADR-0006, so a fresh clone knows.
3. Prove it:

   ```
   python -c "from agent.analytics import predict; print(predict.selected_version())"
   python -m eval.harness --rung 1 --report eval/reports/rung1.json
   ```

   The first prints your pinned version. The harness table is the one that goes in the release.

## Part 5: the A1 pull request, the tag, and the release (15 min)

```
git checkout -b feature/rung1-a1
git add docs/memos/2026-09-24-a1-model-selection.md docs/adr/0006-served-category-model.md .env.example
git status
git commit -m "A1: model-selection memo, served model pinned (ADR-0006)"
git push -u origin feature/rung1-a1
```

PR body: Rung 1, A1; the memo's recommendation in one line; the bake-off table; the harness table for the
pinned model; ADRs 0003 to 0006 listed; checklist; disclosure. When the instructor merges:

```
git checkout main
git pull origin main
git tag -a v0.1 -m "Rung 1: category classifier bake-off, served model pinned"
git push origin v0.1
```

Then on GitHub: **Releases**, **Draft a new release**, choose tag `v0.1`, title `Rung 1`, paste the harness
table and the bake-off table into the notes, attach `eval/reports/rung1.json` and `eval/reports/bakeoff.json`
from your laptop, publish. The release is what the grader opens first, then the memo, then the PRs.

## What A1 is graded on

- The bake-off table with four rows, produced by the script, not typed.
- The memo: one decision, tied to the table, readable by a manager.
- ADRs 0003 to 0006 present, each with every section filled.
- Two model artifacts with cards under `src/agent/models/`, the served one pinned.
- Tag `v0.1` and the release with the report attached.
- Every PR on the way used the template and left `main` green.

## What is next

Module 5 starts Rung 2: the agent reads. Sentence embeddings for "find similar incidents", the knowledge
base search tool, and the KPI functions (MTTR, SLA attainment by priority, backlog aging) computed from the
history CSV. A2 is due Oct 8. The Tuesday breach table and the Hardware column you noticed in Module 2 come
back as the first KPIs.

## Check yourself

1. Your table shows the LLM at 0.95 and the local model at 1.0. Which would you recommend for a desk whose
   real tickets are nothing like this corpus, and what would you ask for before deciding?
2. What breaks if someone trains `category-v0.3` and pushes it without touching `.env`? (Nothing served
   changes, because the pin holds. Without the pin the agent would silently switch models.)
3. Why does the release attach the JSON reports rather than link to the PR? (The PR can be edited; the
   attached file is what the numbers were on the day.)
4. Name one number in your memo a manager could check without opening a terminal, and how.
