# Thursday, Sep 17: "First real classifier" (Rung 1, A1 leg one)

About 75 minutes. This is the first row of the A1 bake-off table (TF-IDF + logistic regression). Gradient
boosting and the LLM classifier fill the other two rows next week; A1 is due Sep 24.

**Before class:** merge Tuesday's PR, pull main, confirm `pytest -q` is green. This page is the checklist and
rubric; the step-by-step walkthrough with expected output is the
[Module 3 lecture](../lectures/03-sla-rung1-eval-prs.md).

## Part 1: the split is a decision (10 min)

Train on March through July, test on August. `agent.analytics.features.time_split` does this with
`cutoff="2026-08-01"`.

Why not a random split: the corpus contains paraphrase families of the same incident, so a random split puts
near-duplicates on both sides and the score lies. August is also where the data has drifted (volume trend,
the slow Hardware category), which is exactly what a deployed model will face.

Write this down as an ADR: copy `docs/adr/0000-template.md` to `docs/adr/0003-time-based-split.md`, one
paragraph per section, and name the model you are about to train in the Decision section. The ADR number
goes into the model card, so write it first.

## Part 2: the baseline (40 min)

1. Implement `build_pipeline()` in `src/agent/analytics/train.py` (the `TODO(student)`). The docstring gives
   the starting hyperparameters. Everything around it, the split, the evaluation, the model card, the
   artifact, is already written; `pytest tests/test_analytics.py` shows the plumbing working with a stand-in
   pipeline.
2. Train:

   ```
   python -m agent.analytics.train --version 0.1 --adr ADR-0003
   ```

   Read the per-class table and the confusion matrix. Then answer one of these in the PR description:

   - If there are misclassifications: which two classes confuse each other most, and what do five of the
     misclassified tickets have in common?
   - If the score is perfect or nearly so: why does a bag of words separate these classes so cleanly? (Look
     at how the corpus was generated, `data/synthetic/generate_tickets.py`, without opening `patterns.yaml`.)
     What about real service-desk text would make this harder? A perfect score on synthetic data is a finding
     about the data, not a result about the model, and the A1 memo should say so.
3. The command wrote `src/agent/models/category-v0.1.joblib` and `category-v0.1.json`. Open the card. Every
   field in it is something a reviewer six weeks from now will need. If the artifact is over a few MB the
   trainer says so; then the ADR must discuss Git LFS before you commit it.

## Part 3: wire it in (25 min)

1. The harness already dispatches Rung 1 to `agent.analytics.predict.classify` and detects the rung from the
   presence of a model. Run it on the holdout set and paste the table into the PR:

   ```
   python -m eval.harness --rung 1 --report eval/reports/rung1.json
   ```

   The 0.80 `classification_accuracy` threshold is now a real gate for the first time. If you are under it,
   say so in the PR and say why; do not lower the threshold (that needs its own ADR).
2. Register inference as a tool. Add `src/agent/tools/schemas/classify_incident.json` with `action_tier`
   `read`, an input schema of `short_description` (required) and `description`, and a description that says
   the result is a suggestion the LLM must not present as fact without the confidence. Add the row to the
   tier table in `docs/governance/governance.md`. Model inference is read tier by course rule.
3. In `src/agent/rung0_poller.py`, call `classify` after the rules and write an `AuditEntry` for it with
   `tool="classify_incident"`, `tier="read"`, and the model version in `inputs`. Every number an agent
   reports must trace to an audited call.

## Deliverable

One PR from branch `feature/rung1-baseline` with:

- `docs/adr/0003-time-based-split.md`
- `build_pipeline()` implemented; `src/agent/models/category-v0.1.joblib` + `.json` committed (or the LFS
  discussion in the ADR if it is large)
- the tool schema and the governance row
- the harness table for `--rung 1` and your confusion-pair answer in the PR description

No tag yet; `v0.1` comes with the full A1 PR on Sep 24.

## Rubric (checklist)

| Item | Meets | Partial | Missing |
|---|---|---|---|
| ADR-0003 | explains the leak a random split would cause, names the model | describes the split without the why | absent |
| Pipeline | TF-IDF + LR trained on the time split; per-class table read, confusions or the perfect-score question discussed | trains, no discussion | random split or trains on `incidents_open.csv` |
| Model card | committed with the artifact, `adr` field set, data hash present | card missing fields | artifact without card |
| Harness | `--rung 1` table in the PR, threshold outcome stated honestly | run but not reported | not run |
| Tool + audit | schema at read tier, governance row, audited call in the poller | schema without governance row | inference called with no audit entry |
