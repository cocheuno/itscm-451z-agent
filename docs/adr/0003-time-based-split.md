# ADR-0003: Time-based train/test split for the category classifier
- **Status:** Accepted
- **Date:** 2026-09-17
- **Rung/Module:** Rung1/Module 3
- **Related Issue/PR:** #

## Context
The classifier is trained on data/eval/incidents_history.csv (4,242 closed incidents, March
and will score tickets that arrive after it was trained. The corpus contains paraphrase fam
incident, and August differs from earlier months (volume trend, slow Hardware resolution).

## Decision
Train on tickets opened before 2026-08-01 (3,461 rows) and test on August (781 rows). T
TF-IDF (1-2 grams, min_df 2, sublinear TF) into logistic regression with balanced class we
category-v0.1 with a model card naming this ADR.

## Alternatives considered
- Random 80/20 split: puts paraphrases of the same incident on both sides; the score wo
performance on unseen incidents.
- K-fold cross-validation: same leak, and no single "later" test month to report.

## Consequences
The August test month is smaller than a random 20 percent would be (781 rows). Every
bake-off uses the same split so the rows are comparable. When September data exists,

## Action-tier impact
None. Model inference is read tier.
