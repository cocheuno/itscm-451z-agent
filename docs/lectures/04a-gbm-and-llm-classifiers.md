# Module 4, session 1: build week, classifier and eval harness

Scheduled for Tuesday, Sep 22; run it whenever the Module 3 PR is merged. Syllabus: "Build week:
classifier + eval harness". The two classifiers still missing from the bake-off, the tool registration that
makes model inference part of the agent, and the harness run that proves it. Prerequisite: `main` carries
`category-v0.1` and ADR-0003 (it does, since PR #23). About 60 minutes of guided work; the pull request is
the rest.

## Where the repository already stands

Some of this session's steps landed on `main` directly, outside a PR, in the week after the Module 3 PR
merged. Check this table before you start so you do not redo finished work or skip unfinished work.

| Step | State on `main` | What you still do |
|---|---|---|
| ADR-0004 (Step 1) | `docs/adr/0004-gradient-boosting-candidate.md` exists; every section has text; the header still reads `ADR-NNNN: <short title>` with the wrong rung | Complete the header |
| `gbm` branch of `build_pipeline` (Step 2) | Done; both pipeline tests pass | Read it, run the test, nothing to write |
| `category-v0.2` (Step 3) | Not trained; only v0.1 is under `src/agent/models/` | Train it |
| API key (Step 5) | Per machine, never committed | Put yours in `.env` |
| `classify_incident` tool schema, governance row, ADR-0005 (Step 7) | Not present | Write all three |
| Audit entry in the poller (Step 8) | Not present | Write it |
| Bake-off run and report (Part 3) | Not run | Run it |

One housekeeping item is fixed in the same PR as this lecture: the ADR template, `docs/adr/0000-template.md`,
had been renamed into ADR-0004 by the GitHub web editor instead of copied, so the `cp` commands in lectures
03 and 04 pointed at a file that no longer existed. It is restored. When you edit on github.com, use "copy"
or create a new file and paste; the editor's rename moves the original.

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
- **Pickle**: how scikit-learn saves a trained model (`.joblib`). It is only guaranteed to load under the
  scikit-learn version that wrote it, which is why `requirements.txt` pins the version.

## Before you start

```
git checkout main
git pull origin main
python -m pip install -r requirements.txt
pytest -q
python -c "from agent.analytics import predict; print(predict.versions())"
```

Expected: pip finishes without errors (it may downgrade scikit-learn to 1.5.2; that is the pin); pytest
ends `70 passed, 1 skipped`; the last line prints `['0.1']`.

If pytest fails on `test_installed_scikit_learn_matches_every_committed_model_card`, the pip step did not
take; run it again and read its output. If the last line prints `[]`, your clone is behind `main`.

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

### Step 1: complete ADR-0004

The ADR exists on `main` but was saved with the template's header. Open
`docs/adr/0004-gradient-boosting-candidate.md` and fix the first five lines so they read:

```
# ADR-0004: Gradient boosting as the second category-model candidate
- **Status:** Accepted
- **Date:** 2026-09-29
- **Rung/Module:** Rung 1 / Module 4
- **Related Issue/PR:** #<the PR you open at the end of this session>
```

The rung is 1, not 3: this is still the "classify and suggest" rung; Rung 3 is when the agent writes. Fill
the PR number after you open the PR, in the same branch, before you mark it ready for review.

Read the body against this checklist and add what is missing. Context: the bake-off needs a non-linear
candidate on the same split. Decision: TF-IDF, SVD to 50 components, histogram gradient boosting, saved as
`category-v0.2`, same time split as ADR-0003. Alternatives: gradient boosting directly on the sparse TF-IDF
(slow, and a much larger artifact); a random forest (similar, less accurate on text). Consequences: the
artifact is about 2.7 MB compressed, under the "few MB" limit; `random_state=451` makes retraining
reproducible; the artifact loads only under the pinned scikit-learn. Action-tier impact: none.

If you ever need a fresh ADR, copy the template, never rename it:

```
cp docs/adr/0000-template.md docs/adr/000N-<short-title>.md
```

### Step 2: read the `gbm` branch (already written)

Open `src/agent/analytics/train.py`. The imports at the top of the file include `TruncatedSVD` and
`HistGradientBoostingClassifier`, and `build_pipeline` ends with:

```python
    tfidf = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    if kind == "lr":
        return make_pipeline(tfidf, LogisticRegression(max_iter=1000, class_weight="balanced"))
    return make_pipeline(tfidf, TruncatedSVD(n_components=50, random_state=451),
                         HistGradientBoostingClassifier(random_state=451))
```

Three things to be able to say about it: the same `tfidf` object is shared by both branches, so the two
models see identical features; `random_state=451` appears twice because both SVD and boosting use
randomness; and 50 components rather than 100 is a size decision (4.7 MB at 100, over the limit), not an
accuracy one. Confirm with:

```
pytest tests/test_analytics.py -v
```

Both `test_build_pipeline_returns_a_fit_predict_pipeline_once_implemented` cases pass. Nothing to write.

### Step 3: train it

```
python -m agent.analytics.train --version 0.2 --adr ADR-0004 --pipeline gbm
```

Expected: the same report shape as Module 3, about two seconds to fit, `accuracy 0.994  macro F1 0.990`
give or take a few thousandths, and `saved src/agent/models/category-v0.2.joblib (2.7 MB)`. Open the two
cards side by side. Same `training_data.sha256`, same split, different `pipeline`, different `adr`, a
`kind` field of `gbm`, and the same `environment.scikit-learn` as v0.1. That is what "models are
change-managed artifacts" looks like.

Run `pytest -q` again. Still green: the version-match test now checks two cards. If it fails, you trained
under a different scikit-learn than the pin; run the pip step from "Before you start" and train again.

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
  parse prose, and the model cannot invent a seventh category. The `confidence` field is a plain number
  with its 0-to-1 range stated in its `description`, because the API accepts only a subset of JSON Schema
  in this position (types, enums, `additionalProperties: false`) and rejects `minimum`/`maximum` with a
  400. `parse_response` clamps the value to [0, 1] on the way in.
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
per million is $0.00063. Real tickets have longer descriptions; over the 40-ticket eval set the measured
average is about $0.0012 per ticket, so the eval set costs about five cents and the whole 4,242-ticket
history about five dollars. Write down the price you used; it goes in the memo, and prices change.

If it fails: `Anthropic API 401` means the key is wrong or missing; `429` means you are sending too fast
(the bake-off sends one at a time, so this happens only with a shared key); `400` naming
`output_config.format.schema` means the schema uses a keyword structured outputs do not accept (the test
`test_schema_uses_only_keywords_structured_outputs_accept` guards against this, so run `pytest -q` first);
`400` naming `output_config` alone means the model in `.env` does not support structured output, so use
the default.

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

Then three more edits, all in this PR, because CONTRIBUTING rule 4 says a new tool needs an ADR and a
governance update together:

1. **Governance row.** In `docs/governance/governance.md`, section 2, add
   `| classify_incident | read | — | — |` under `find_similar_incidents`.
2. **ADR-0005.** `cp docs/adr/0000-template.md docs/adr/0005-classify-incident-tool.md`. Short. Context:
   the agent needs model inference as a tool it can call and audit. Decision: `classify_incident` at the
   read tier, served by `agent.analytics.predict.classify`, the LLM path stays in the bake-off. Alternatives:
   call `predict.classify` directly from the agent loop (no audit, no tier; rejected). Consequences: one
   audit entry per suggestion. Action-tier impact: adds a read-tier tool; governance.md updated in this PR.
3. **Check the tests still pass.** `pytest -q`. The registry loads every schema in the folder, so the tier
   tests now cover four tools. The MCP server test still lists three, which is correct: the MCP server
   exposes only the ServiceNow read tools (Module 5 adds the closures by name), and `classify_incident` is
   called inside the agent, not offered to outside clients.

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

Run the poller on a few tickets. `--since` takes a ServiceNow timestamp, `YYYY-MM-DD HH:MM:SS` in quotes, in
UTC unless the service account has its own time zone (Central Daylight Time plus five hours). All 150 open tickets were created within a minute or two of
each other when you seeded, so pick a time a few seconds before the end of that run; a time before it
returns all 150, a time after it returns nothing. If you do not remember it, open the incident list in the
PDI sorted by Created, newest first.

```
python -m agent.rung0_poller --since "2026-09-29 18:00:00" --dry-run
```

Expected: one line per ticket, the number and the rule result. Open `logs/audit.jsonl`: each ticket now has
two entries, `rules` and `classify_incident`. The model's number is traceable to an audited call. That is
what "every number in an agent answer must be traceable" means in code.

## Part 3: four rows (5 min)

```
python scripts/bakeoff.py --report eval/reports/bakeoff.json
```

With a key in `.env` this runs all four rows over the 40 eval tickets (the LLM row takes about a minute).
Measured on the instructor's machine, Oct 6:

```
| Row | n | Accuracy | Macro F1 | Latency ms | Cost $/pred | Unclassified |
|---|---|---|---|---|---|---|
| rules | 40 | 0.15 | 0.15 | 0.0 | 0.0 | 33 |
| model:0.1 | 40 | 1.0 | 1.0 | 5.25 | 0.0 | 0 |
| model:0.2 | 40 | 1.0 | 1.0 | ~3 | 0.0 | 0 |
| llm | 40 | 0.625 | 0.665 | 1275.04 | 0.001232 | 0 |
```

Your LLM row will differ from run to run; the other rows should be close, and latencies depend on the
laptop. Read the table before Thursday:

- The two local models are perfect because the synthetic corpus is separable by vocabulary. That is a
  property of the data, not evidence about real tickets; the memo must say so.
- The LLM is the only row that never saw the training data. It knows what a network problem is in general
  but not this corpus's conventions, which is why its weakest class is Software (tickets this taxonomy files
  under Inquiry / Help or Database read as "software" to a general model). Look at the per-class table
  underneath to see it.
- `--report` writes the JSON the release attaches. `eval/reports/` is git-ignored except its `.gitkeep`,
  so the file never enters a commit; paste the table into the PR body instead.

## Deliverable

```
git checkout -b feature/rung1-bakeoff-models
git add docs/adr/0004-gradient-boosting-candidate.md docs/adr/0005-classify-incident-tool.md \
        src/agent/models/category-v0.2.joblib src/agent/models/category-v0.2.json \
        src/agent/tools/schemas/classify_incident.json docs/governance/governance.md src/agent/rung0_poller.py
git status
git commit -m "Rung 1: gradient boosting v0.2 (ADR-0004), classify_incident tool (ADR-0005), bake-off run"
git push -u origin feature/rung1-bakeoff-models
```

`train.py` is not in the list because the `gbm` branch is already on `main`; if `git status` shows it
modified, you changed something by accident, so `git diff src/agent/analytics/train.py` and decide.
`git status` must not show `.env`, `eval/reports/bakeoff.json`, or `logs/`.

PR body, from the template: Rung 1; what changed (the second model, the tool, the audit entry); eval results
from `python -m eval.harness --rung 1` (now served by v0.2) with the Module 3 numbers as "Before"; the
bake-off table pasted from the terminal; ADRs 0004 and 0005; checklist; disclosure. After the PR exists,
put its number in ADR-0004's header and push again.

## Check yourself

1. Why does the gradient-boosting pipeline have an SVD step and the logistic-regression one does not?
2. The LLM row costs about $0.0012 per prediction and the local rows cost nothing. At 700 tickets a month,
   what is the annual difference, and what would make it worth paying? (About $10 a year; only an accuracy
   gain the desk can feel, and on this table the LLM is the less accurate row.)
3. What stops the model from returning "Printer" as a category?
4. The poller now writes two audit entries per ticket. Which one may influence what a customer is told?
   (Neither, today. Rung 2 lets the agent narrate; the rule about predictions as facts still applies.)
5. Why can a `.joblib` trained on one laptop fail to load on another, and what in this repository prevents
   it? (It is a pickle tied to the scikit-learn version; the pin in `requirements.txt` and the version-match
   test.)
