# Module 3: "First real classifier" (Rung 1, A1 leg one)

About 75 minutes. This is the first model row of the A1 bake-off (TF-IDF plus logistic regression). The
other two rows come in Module 4. This page is the checklist and rubric; the step-by-step walkthrough with
every command and what it prints is the [Module 3 lecture](../lectures/03-sla-rung1-eval-prs.md).

## Before class

- Module 2 committed on `module-02` with tag `v0.0`.
- `git checkout main`, `git pull origin main`, `python -m pytest -q` green, then
  `git checkout -b module-03`.

## Part 1: SLA (15 min)

- [ ] `docs\sla.md` written: five-row target table, clock rule, pause rule, communication table with
      authors.
- [ ] `TARGETS_MIN` set and the `TODO` line removed; `python -m pytest tests\test_sla.py -v` all `PASSED`.
- [ ] You can say, from the Module 2 breach table, three explanations for the P1 rate that the table cannot
      tell apart.

## Part 2: prediction versus rule (10 min)

- [ ] You can fill in the five-row comparison table (input, how, can be wrong, needs a confidence, who may
      do it) from memory.
- [ ] You found the rung 1 line in `eval\harness.py` and can say what `pred_priority` comes from.

## Part 3: the classifier (35 min)

- [ ] ADR-0003 read; three sentences in your journal in your own words.
- [ ] The two pipeline lines read; you can say what `min_df`, `sublinear_tf`, `ngram_range` and
      `class_weight` each do.
- [ ] `python -m agent.analytics.train --version 0.1 --adr ADR-0003` run; per-class table read.
- [ ] `git diff` of the model card read; you can name which fields differ from the instructor's and why.
- [ ] Journal says in your words why the score is perfect and what would make real text harder.

## Part 4: scoring (10 min)

- [ ] Harness table for `--rung 1` in the journal; you can explain each of the five lines.
- [ ] Bake-off with `--rows rules,model:0.1` in the journal.

## Deliverable

- [ ] `docs\journal\module-03.md` with the six headings from the lecture.
- [ ] One commit on `module-03` with the five files; `git status` clean of `.env`, reports and logs.

## Rubric

| Item | Meets | Partial | Missing |
|---|---|---|---|
| SLA page | table, clock rule, pause rule, communication authors; targets in code, tests pass | table only | absent or tests fail |
| Split explained | three sentences that name the leak a random split causes | restates the ADR | copied or absent |
| Training | run on the time split; per-class table and confusion matrix read aloud | run, not read | random split, or trained on `incidents_open.csv` |
| Perfect score | explained as a property of the synthetic text, with what real text changes | "the model is good" | not addressed |
| Harness | `--rung 1` table in the journal, each line explained | table only | not run |
| Git | commit on `module-03` with the five files and the journal | commit missing files | work on `main` or nothing committed |
