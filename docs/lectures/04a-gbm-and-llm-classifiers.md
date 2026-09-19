# Module 4, session 1: two more classifiers, gradient boosting and the LLM

Tuesday, Sep 22. Prerequisite: the Module 3 PR (`feature/rung1-baseline`) is merged, so `main` carries
`category-v0.1` and ADR-0003. About 60 minutes of guided work; the pull request is the rest.

## What you will be able to do afterwards

1. Explain in plain words what gradient boosting is and why tree models need a different input than
   logistic regression does.
2. Train a second model with the same plumbing and compare its card with the first.
3. Call the Anthropic API from Python over plain HTTP, read the response, and say what every field costs.
4. Explain why the label set is enforced with a schema and why ticket text is passed as data.
5. Register model inference as an agent tool at the read tier, with an audit entry per call.

## Why this session exists

**Analytics.** The A1 bake-off has four rows: keyword rules (done), TF-IDF plus logistic regression (done),
gradient boosting, and an LLM. Rows 3 and 4 are today. A bake-off is not a search for the best model. It is
how you learn that "best" has four axes, accuracy, per-class behaviour, latency and cost, and that the
answer depends on which axis the service desk is paying for. Gradient boosting is the workhorse of tabular
prediction in industry; the LLM is what everyone reaches for first. Thursday's memo says which this desk
should use.

**The agent.** From Rung 2 onward the agent chooses which tools to call and narrates their results. Model
inference is one of those tools, so today it gets a schema, a tier, and an audit entry, exactly like the
tools that read ServiceNow. That is the course principle in practice: the LLM interprets; deterministic code
and versioned models compute.

## Words you need

- **Decision tree**: a sequence of yes/no questions on the input columns ending in a category.
- **Gradient boosting**: a few hundred small trees trained one after another, each correcting the errors the
  previous ones still make. `HistGradientBoostingClassifier` is scikit-learn's fast version.
- **Dense versus sparse**: TF-IDF produces 5,400 columns per ticket, almost all zero (sparse). Trees want a
  few dozen columns that are all filled in (dense).
- **SVD (singular value decomposition)**: a compression that turns the 5,400 sparse columns into 50 dense
  ones that keep most of the information. `TruncatedSVD` in scikit-learn.
- **API**: a web address you send a request to and get a JSON answer from. The Anthropic Messages API is
  `POST https://api.anthropic.com/v1/messages`.
- **Token**: the unit the API charges by, roughly three quarters of a word. Prices are per million tokens,
  input and output priced separately.
- **JSON schema**: a description of the exact shape of JSON you will accept. Sending one with the request
  makes the API return that shape and nothing else.
- **Latency**: wall-clock time per prediction. Local models take milliseconds; an API call takes a second.
- **Tool schema / tier**: every capability the agent can invoke is described in a JSON file under
  `src/agent/tools/schemas/` with an `action_tier`: read, propose, execute_with_approval, autonomous.

## Before you start

```
git checkout main
git pull origin main
pytest -q
python -c "from agent.analytics import predict; print(predict.versions())"
```

Expected: pytest green; the last line prints `['0.1']`. If it prints `[]`, the Module 3 PR is not merged
or not pulled.

## Part 1: gradient boosting (20 min)

### What it does

Logistic regression draws one straight boundary per category through the word-weight space. A boosted
model builds a few hundred small decision trees in sequence: the first tree makes a rough guess, the second
is trained on what the first got wrong, and so on. The final answer adds up all the trees' votes. Boosting
wins on most tabular problems because it can express "if the ticket mentions printing *and* a floor number,
Hardware; if it mentions printing *and* a report name, Software" without anyone writing that rule.

Trees split on one column at a time, so they need a small number of informative, dense columns. TF-IDF
gives thousands of sparse ones. `TruncatedSVD(n_components=50)` compresses them to 50 dense columns that
capture the main directions of variation in the text; the trees then work on those.

### Step 1: ADR-0004

Every model version names an ADR, and this is a new model, so:

```
cp docs/adr/0000-template.md docs/adr/0004-gradient-boosting-candidate.md
```

Fill every section. Context: the bake-off needs a non-linear candidate on the same split. Decision: TF-IDF,
SVD to 50 components, histogram gradient boosting, saved as `category-v0.2`, same time split as ADR-0003.
Alternatives: gradient boosting directly on the sparse TF-IDF (slow, and a much larger artifact); a random
forest (similar, less accurate on text). Consequences: the artifact is about 2.7 MB compressed, under the
"few MB" limit; `random_state=451` makes retraining reproducible. Action-tier impact: none.

### Step 2: the `gbm` branch

In `src/agent/analytics/train.py`, `build_pipeline` has a line `raise NotImplementedError("gbm: Module 4")`.
Replace it, and add two imports at the top of the function, so the whole function reads:

```python
    from sklearn.decomposition import TruncatedSVD
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    if kind not in PIPELINES:
        raise ValueError(f"unknown pipeline {kind!r}; choose from {PIPELINES}")
    tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    if kind == "lr":
        return make_pipeline(tfidf, LogisticRegression(max_iter=1000, class_weight="balanced"))
    return make_pipeline(tfidf, TruncatedSVD(n_components=50, random_state=451),
                         HistGradientBoostingClassifier(random_state=451))
```

`pytest tests/test_analytics.py -v` now passes both pipeline tests instead of skipping the second.

### Step 3: train it

```
python -m agent.analytics.train --version 0.2 --adr ADR-0004 --pipeline gbm
```

Expected: the same report shape as Module 3, about two seconds to fit, `accuracy 0.994  macro F1 0.990`
give or take a few thousandths, and `saved src/agent/models/category-v0.2.joblib (2.7 MB)`. Open the two
cards side by side. Same `training_data.sha256`, same split, different `pipeline`, different `adr`, and
now a `kind` field. That is what "models are change-managed artifacts" looks like.

### Step 4: which model does the agent serve?

`predict.classify` serves the newest version unless told otherwise, so after this step the harness uses
v0.2. The memo on Thursday chooses. Until then, nothing to do, but know where the choice lives:
`CATEGORY_MODEL_VERSION` in `.env` (see `.env.example`). Leave it empty for now.

## Part 2: the LLM classifier (30 min)

### How an API call works

You send a JSON request to the Anthropic Messages API with the model name, a system prompt (standing
instructions), a message (the ticket), and a limit on the answer length. You get back JSON with the answer,
the model that produced it, and the token counts. The course does this with the `requests` library and no
SDK until Module 7 (COURSE_CONTEXT), so what you read is the whole mechanism.

The module `src/agent/analytics/llm_classify.py` is written. Open it and read it with these notes:

- `CATEGORIES` and `SCHEMA`: the six labels, and a JSON schema whose `category` is an enum of exactly
  those six. `output_config.format` in the request makes the API return JSON matching the schema. You never
  parse prose, and the model cannot invent a seventh category.
- `SYSTEM`: the standing instruction. It says the text inside `<ticket>` tags was written by an end user
  and is data to classify. That sentence is the rule from `governance.md` section 5 applied at the prompt.
- `request_body`: builds the request. `max_tokens=64` because a label and a number need a few tokens; a
  larger budget costs money and adds nothing. No thinking budget for the same reason.
- `parse_response`: reads the first text block, parses the JSON, reads `usage.input_tokens` and
  `usage.output_tokens`, and prices them from `PRICES_PER_MTOK`. If the model in `.env` is not in that
  table, `cost_usd` is `None` and you add the row yourself from the price sheet.
- `classify`: the function the bake-off and the harness call. Returns `pred_category`, `confidence`,
  `model`, token counts, `cost_usd`, `latency_ms`.

The `confidence` the model writes is not a calibrated probability. It is useful for ranking and for the
"never present a prediction as a fact" rule; A4 covers calibration properly.

### Step 5: a key

1. Sign in at `console.anthropic.com` (or use the key the instructor gives you). Open **API Keys**, create
   one named `itscm451z`, copy it once; it is not shown again.
2. In `.env`: `ANTHROPIC_API_KEY=` followed by the key, no quotes. Leave `ANTHROPIC_MODEL` as it is unless
   the instructor says otherwise. Never paste the key anywhere else, and never commit `.env`.
3. `python -m agent.config` must still print `config ok`.

### Step 6: one ticket

```
python -m agent.analytics.llm_classify "VPN drops every hour" "Started after the Friday patch, wired works"
```

Expected, in about a second:

```
{
  "pred_category": "Network",
  "confidence": 0.9,
  "model": "claude-sonnet-4-6",
  "input_tokens": 110,
  "output_tokens": 20,
  "cost_usd": 0.00063,
  "latency_ms": 900
}
```

Your numbers will differ. Read the cost: 110 input tokens at $3 per million plus 20 output tokens at $15
per million is $0.00063. A ticket with a long description costs about a tenth of a cent; the 40-ticket eval
set about five cents; the whole 4,242-ticket history about five dollars. Write down the price you used; it
goes in the memo, and prices change.

If it fails: `Anthropic API 401` means the key is wrong or missing; `429` means you are sending too fast
(the bake-off sends one at a time, so this happens only with a shared key); `400` with a message about
`output_config` means the model in `.env` does not support structured output, so use the default.

### Step 7: register it as a tool

The agent may only call what has a schema and a tier. Create `src/agent/tools/schemas/classify_incident.json`:

```json
{
  "name": "classify_incident",
  "description": "Suggest a category for an incident from its text, with a confidence. The result is a suggestion from a model, not a decision; never state it to a customer as fact, and never use it to set priority.",
  "action_tier": "read",
  "input_schema": {
    "type": "object",
    "properties": {
      "short_description": {"type": "string"},
      "description": {"type": "string"}
    },
    "required": ["short_description"],
    "additionalProperties": false
  }
}
```

Add a row to the tier table in `docs/governance/governance.md`: `| classify_incident | read | — | — |`.
Adding a tool needs an ADR (CONTRIBUTING rule 4): `docs/adr/0005-classify-incident-tool.md`, short, with
"Action-tier impact: adds a read-tier tool; governance.md updated in this PR".

### Step 8: the audit entry

Every call the agent makes is logged. In `src/agent/rung0_poller.py`, after the rules are applied, add the
model's suggestion with its own audit entry. Inside the loop in `main()`, after the existing `log.write(...)`
and before the `print`:

```python
        from agent.analytics.predict import classify  # the served model; the LLM path is the bake-off's
        suggestion = classify(t)
        log.write(AuditEntry(ticket=t["number"], tool="classify_incident", tier="read",
                             inputs={"model_version": suggestion["model_version"]},
                             reasoning="category model suggestion",
                             outcome=str({"pred_category": suggestion["pred_category"],
                                          "confidence": suggestion["confidence"]})))
```

Run the poller on a few tickets (`--since` a recent time) and open `logs/audit.jsonl`: each ticket now has
two entries, `rules` and `classify_incident`. The model's number is traceable to an audited call. That is
what "every number in an agent answer must be traceable" means in code.

## Part 3: four rows (5 min)

```
python scripts/bakeoff.py
```

With a key in `.env` this runs all four rows over the 40 eval tickets (the LLM row takes about a minute).
Expected shape:

```
| Row | n | Accuracy | Macro F1 | Latency ms | Cost $/pred | Unclassified |
|---|---|---|---|---|---|---|
| rules | 40 | 0.15 | 0.15 | 0.0 | 0.0 | 33 |
| model:0.1 | 40 | 1.0 | 1.0 | 17.5 | 0.0 | 0 |
| model:0.2 | 40 | 1.0 | 1.0 | 12.8 | 0.0 | 0 |
| llm | 40 | 0.95 | 0.93 | 950.0 | 0.0006 | 0 |
```

Your LLM row will differ; the other rows should be close. Save it: add `--report eval/reports/bakeoff.json`
and paste the table into the PR. Thursday turns it into the memo.

## Deliverable

```
git checkout -b feature/rung1-bakeoff-models
git add docs/adr/0004-gradient-boosting-candidate.md docs/adr/0005-classify-incident-tool.md \
        src/agent/analytics/train.py src/agent/models/category-v0.2.joblib src/agent/models/category-v0.2.json \
        src/agent/tools/schemas/classify_incident.json docs/governance/governance.md src/agent/rung0_poller.py
git status
git commit -m "Rung 1: gradient boosting v0.2 (ADR-0004), classify_incident tool (ADR-0005), bake-off run"
git push -u origin feature/rung1-bakeoff-models
```

PR body: Rung 1; what changed (the two models, the tool, the audit entry); eval results from
`python -m eval.harness --rung 1` (now served by v0.2) with the Module 3 numbers as "Before"; the bake-off
table; ADRs 0004 and 0005; checklist; disclosure. `git status` must not show `.env` or `eval/reports/`.

## Check yourself

1. Why does the gradient-boosting pipeline have an SVD step and the logistic-regression one does not?
2. The LLM row costs $0.0006 per prediction and the local rows cost nothing. At 700 tickets a month, what
   is the annual difference, and what would make it worth paying? (About $5 a year; only an accuracy gain
   the desk can feel, which this table does not show.)
3. What stops the model from returning "Printer" as a category?
4. The poller now writes two audit entries per ticket. Which one may influence what a customer is told?
   (Neither, today. Rung 2 lets the agent narrate; the rule about predictions as facts still applies.)
5. Where is the served model version decided, and who decides it?
