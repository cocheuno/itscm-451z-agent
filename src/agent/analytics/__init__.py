"""Analytics/ML thread (COURSE_CONTEXT.md): pure functions over DataFrames, models as versioned artifacts.

Modules arrive by rung: features.py + train.py + predict.py (Rung 1, A1); metrics.py (A2); drift.py (A6);
forecast.py (M11). Nothing here calls an LLM; the LLM only chooses which of these to consult and narrates.
"""
