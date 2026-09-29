# ADR-NNNN: <short title>
- **Status:** Proposed | Accepted | Superseded by ADR-NNNN
- **Date:** YYYY-MM-DD
- **Rung/Module:**
- **Related Issue/PR:** #

## Context
The bake-off needs a non-linear candidate on the same split.

## Decision
TF-IDF, SVD to 50 components, histogram gradient boosting, saved as category-v0.2

## Alternatives considered
Gradient boosting directly on the sparse TF-IDF (slow, and a much larger artifact); a random forest (similar, less accurate on text).

## Consequences
The artifact is about 2.7 MB compressed, under the "few MB" limit; random_state=451 makes retraining reproducible.

## Action-tier impact
None
