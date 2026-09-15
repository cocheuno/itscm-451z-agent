# Model artifacts

One trained model = one `<task>-v<version>.joblib` plus one `<task>-v<version>.json` model card, written by
`python -m agent.analytics.train`. The card records the training-data hash, the split, the metrics, the ADR
that chose the model, and the library versions. `agent.analytics.predict` loads the newest version that has
both files; a card without an artifact, or the reverse, is ignored.

Rules (COURSE_CONTEXT.md, "Models are change-managed artifacts"):

- Every version has an ADR. The card's `adr` field names it.
- Artifacts under a few MB are committed with their card. Anything larger needs a Git LFS decision in an ADR
  before it is committed; `train.py` warns at 3 MB.
- Never retrain in place. A new run is a new version, even for the same code, because the data hash may differ.
