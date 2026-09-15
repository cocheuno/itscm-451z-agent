# %% [markdown]
# # First look at the incident history
#
# Rung 0 close-out, Tuesday Sep 15 (docs/exercises/2026-09-15-rung0-closeout.md).
#
# This file is a notebook in VS Code cell format: open it, and each `# %%` block runs as a cell
# (Run Cell / Shift+Enter). It also runs top to bottom as a plain script, and ruff lints it like any other
# module. If you prefer .ipynb, "Export as Jupyter Notebook" from the cell toolbar, but commit this .py file.
#
# Data: `data/eval/incidents_history.csv`, the authoritative closed-incident corpus (ADR-0002). Do not use
# `data/eval/incidents_open.csv` here; its `gt_*` columns are grading ground truth.

# %%
import pandas as pd

from agent.analytics import features

pd.set_option("display.width", 120)
df = features.load_history()
print(df.shape)
print(df.head())

# %% [markdown]
# ## Question 1: volume by weekday
# How many incidents opened on each weekday? Which day is busiest, and by how much versus the median day?

# %%
by_weekday = df["opened_at"].dt.day_name().value_counts().reindex(
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
print(by_weekday)

# %% [markdown]
# ## Question 2: category mix
# Share of incidents per category, and the top three subcategories inside the largest category.

# %%
category_share = df["category"].value_counts(normalize=True).round(3)
print(category_share)

# %%
# TODO(student): top three subcategories within the largest category.

# %% [markdown]
# ## Question 3: median resolve time by category and month
# `resolve_minutes` is resolved_at minus opened_at. Build a table with months as rows and categories as
# columns. Does any category move in one direction over the six months?

# %%
df["month"] = df["opened_at"].dt.to_period("M")
mttr = df.pivot_table(index="month", columns="category", values="resolve_minutes", aggfunc="median").round(0)
print(mttr)

# %% [markdown]
# ## Question 4: breach rate by priority
# `made_sla` is False when the ticket missed its resolution target. Breach rate per priority, with counts.

# %%
breach = df.groupby("priority").agg(n=("made_sla", "size"), breach_rate=("made_sla", lambda s: 1 - s.mean())).round(3)
print(breach)

# %% [markdown]
# ## Optional: two charts
# Weekly volume over time, and the monthly median resolve time per category.

# %%
try:
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7))
    df.set_index("opened_at").resample("W")["number"].count().plot(ax=ax1, title="incidents opened per week")
    mttr.plot(ax=ax2, title="median resolve minutes by category and month")
    fig.tight_layout()
except ImportError:
    print("matplotlib not installed; skip the charts")

# %% [markdown]
# ## Five observations
#
# Write five sentences here, each naming a number from a table above. An observation is "Hardware's median
# resolve time rose from N in March to M in August", not "Hardware got slower". Naming a pattern is not the
# same as measuring it; A2 asks for the measuring.
#
# 1.
# 2.
# 3.
# 4.
# 5.
