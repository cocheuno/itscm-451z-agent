# COURSE_CONTEXT.md

Context brief for AI-assisted development sessions on this repository.
Read this fully before making changes. It encodes decisions already made;
do not relitigate them, and ask before deviating.

## What this repository is

The semester-long build for **ITSCM 451Z — Managing Information Technology
Services** (UW-Whitewater, Fall 2026). One student (a business analytics
major, senior), one instructor (Timothy E. Carone), run as an apprenticeship.
The student builds an AI agent that executes — and analyzes — IT Service
Management processes against a ServiceNow Personal Developer Instance (PDI).

The course has three threads woven through every module:

1. **The capability ladder** — the agent grows one rung at a time.
2. **Version management** — every assignment is a merged PR plus a Git tag;
   Git practice is graded content.
3. **Analytics/ML** — the agent measures and models the service it operates.
   Supervised and unsupervised learning applied to ITSM operational data.

## Non-negotiable design principles

- **Deterministic computation, LLM interpretation.** The LLM never computes
  a number and never *is* the analytical model. Metrics are computed by plain,
  testable Python (pandas). Trained models (sklearn) are versioned artifacts
  wrapped as tools. The LLM chooses which tools/models to consult and
  narrates results. Every number in an agent answer must be traceable to an
  audited tool call.
- **Action tiers.** Every tool declares read / propose / execute-with-approval
  / autonomous (`src/agent/tools/tiers.py`). Analytics and model-inference
  tools are **read** tier. Recommendations (prescriptive analytics) are
  **propose** tier. The registry enforces tiers; do not bypass it.
- **Audit everything.** All agent actions flow through `src/agent/audit.py`
  (inputs, reasoning, tool, outcome, timestamp; append-only). New code paths
  must log.
- **Models are change-managed artifacts.** Each trained model version is
  stored under `src/agent/models/` as a serialized artifact plus a
  model-card JSON (training data hash, features, metrics, date, ADR link).
  Retraining is a change; deploying a model version rides a release tag.
- **Writes are earned.** No code writes to the PDI until Rung 3, and then
  only through tiered, approved, rollback-tested paths.
- **Everything through PRs.** Branch per piece of work; PR into protected
  `main`; CI (`.github/workflows/eval.yml`) must pass; tag releases
  (`scripts/make_release.sh`). Significant decisions get an ADR in
  `docs/adr/` (template: `0000-template.md`), merged with the code they
  govern.
- **No agent framework before Module 7.** Raw Anthropic API + requests until
  the hand-built loop hurts; adopting a framework requires an ADR.
- **Secrets never enter the repo.** `.env` only (gitignored); pre-commit
  scanning is active. CI runs offline — no PDI credentials or API keys in
  GitHub Actions.

## The capability ladder (fixed)

| Rung | Capability | Modules | Tag |
|---|---|---|---|
| 0 | Deterministic ticket poller — no AI; proves API, audit, Git | M2 | v0.0 |
| 1 | Ticket classification + priority vs. SLA rules, with eval harness | M3–M4 | v0.1 |
| 2 | Read-only triage agent: semantic KB/similar-incident retrieval, KPI tools | M5–M6 | v0.2 |
| 3 | Write actions under guardrails: tiers, approvals, audit, rollback | M7–M8 | v0.3 |
| 4 | Request→approval→fulfillment→closure workflow; SLA timers + breach-risk scoring | M9–M10 | v0.4 |
| 5 | Problem/Change: incident clustering → problem candidates → drafted RFCs, simulated CAB | M13 | v0.5 |
| 6 | Observability: eval dashboard, failure injection, drift detection, cost/latency | M14 | v1.0-rc |
| — | Capstone: live demo with injected failure + "ask the service desk anything" | Finals | v1.0 |

## The analytics/ML thread by module (fixed placement)

- **M3–M4 (A1, due Sep 24):** classifier **bake-off** on shared ground truth:
  TF-IDF + logistic regression baseline vs. gradient boosting vs. LLM
  classification. Report precision/recall/F1, confusion matrices, and
  cost + latency per prediction. Deliverable includes a model-selection
  recommendation memo.
- **M5–M6 (A2, due Oct 8):** embeddings (sentence-transformers, local) for
  `find_similar_incidents` and `search_kb`; descriptive KPI tools — MTTR,
  MTTA, SLA attainment by priority, backlog aging, category Pareto —
  validated against seeded patterns; agent-narrated Service Desk Health
  Report.
- **M7–M8 (A3, due Oct 22):** models-as-artifacts governance (model cards as
  ADRs); diagnostic analytics: change-induced incident correlation.
- **M9 (BCP):** anomaly detection on ticket volume (residual-based or
  isolation forest) wired to the agent-failure runbook — an anomaly triggers
  degraded mode.
- **M10 (A4, due Nov 5):** supervised SLA **breach-risk scoring** (logistic
  regression; calibration required) feeding workflow SLA timers: high risk →
  early escalation.
- **M11:** ticket-volume **forecasting** with weekly seasonality; capacity
  planning computed from the forecast.
- **M12 (A5, due Nov 19):** adversarial ML in the red team: training-data
  poisoning attempt against the retraining path, plus prompt injection via
  ticket text and data-leakage probes.
- **M13:** **unsupervised clustering** of resolved incidents (embed, then
  k-means and HDBSCAN; silhouette/stability evaluation); coherent cluster →
  problem candidate → agent-drafted problem record and RFC.
- **M14 (A6, due Dec 10):** **drift detection** (input drift and performance
  drift) on the classifier; retraining-trigger policy written into
  `docs/governance/governance.md`; agent self-analytics (cost, latency,
  accuracy trends).

## Repository conventions (as they exist — conform, don't churn)

Layout: code in `src/agent/` (servicenow client under `src/agent/servicenow/`,
tools + JSON schemas under `src/agent/tools/`, workflow under
`src/agent/workflow/`); eval harness in `eval/` (`harness.py`, `metrics.py`,
`thresholds.yaml`, failure injection under `eval/failure_injection/`);
synthetic data tooling in `data/synthetic/`; generated eval data in
`data/eval/`; ADRs in `docs/adr/`; governance in `docs/governance/`;
runbooks in `docs/runbooks/`; tests in `tests/`. Keep the suite green:
run `pytest` before and after changes. Table-name constants live in
`src/agent/servicenow/tables.py` — never inline table-name strings.

New packages to create for the analytics thread:
- `src/agent/analytics/` — `metrics.py` (KPIs), `features.py`,
  `train.py` / `predict.py`, `drift.py`, `forecast.py`. Pure functions over
  DataFrames wherever possible; unit-tested against fixture data in
  `tests/fixtures/`.
- `src/agent/models/` — versioned model artifacts (`joblib`) + model-card
  JSON per version. Large binaries: if an artifact exceeds a few MB, discuss
  Git LFS in an ADR before committing.

Dependencies to add (one small PR, needed by Sep 8):
`scikit-learn`, `sentence-transformers`, `matplotlib`, `statsmodels`,
`joblib` — append to `requirements.txt`; keep versions floored (`>=`)
consistent with existing style.

## PRIORITY TASK: historical synthetic data generator (needed by Sep 15)

Rewrite `data/synthetic/generate_tickets.py` and `data/synthetic/taxonomy.yaml`
to produce a **historical corpus**, not just open tickets: ~6 months
(roughly 2026-03-01 to 2026-08-31) of closed incidents — target on the order
of 3,000–5,000 — plus a small current set of open tickets, with realistic
fields: open/close timestamps, category/subcategory, impact, urgency,
priority (derived impact × urgency), assignment group, resolution times,
reassignment counts, reopen flags, close notes, and SLA breach outcomes.

**Seeded truth (the whole point).** The corpus must contain deliberately
injected, later-recoverable structure. All pattern parameters must be
config-driven (extend `taxonomy.yaml` or add `patterns.yaml`) and driven by
a **fixed random seed** so the corpus is reproducible. Inject:

1. **Five latent problem clusters** — five distinct recurring root causes,
   each expressed as a family of incidents with paraphrased-but-related
   short descriptions (vary wording; do not template-stamp identical
   strings, or clustering becomes trivial). Cluster sizes ~40–120 each.
   The student's M13 clustering must recover these.
2. **One change-caused incident spike** — a synthetic change record (or a
   documented change date) followed within 24–72h by a burst of related
   incidents in affected categories. The M7–M8 correlation analysis must
   find it.
3. **Weekly seasonality + trend** — Monday-morning volume peaks, quiet
   weekends, and a mild upward trend across the 6 months. The M11 forecast
   must capture the seasonality.
4. **Degrading MTTR in one category** — one category whose resolution times
   worsen month over month. The A2 descriptive KPIs must surface it.
5. **Learnable-but-imperfect breach signal** — SLA breach correlates with
   features like priority, category, assignment group load, and hour-of-day,
   with enough noise that a well-built logistic model lands roughly in the
   AUC 0.75–0.85 range, not 0.99. The M10 risk scorer trains on this.
6. **A small poisoning-bait subset** (for M12): a handful of adversarially
   worded tickets (e.g., instructions embedded in short_description) flagged
   in the manifest, unlabeled in the corpus.

**The manifest.** The generator must emit a `seeded_truth_manifest.json`
(cluster membership by ticket, spike window and change reference, trend and
seasonality parameters, the degrading category, breach-signal coefficients,
poison-bait IDs). **The manifest is instructor-only: it must NOT be committed
to this repository.** Write it outside the repo or to a path covered by
.gitignore, and say clearly in the PR where it landed. The grading flow is:
instructor holds the manifest; student analytics are scored against it.

**Loading.** The corpus loads to the PDI via `scripts/seed_pdi.py` (extend it
for closed incidents with historical timestamps — note ServiceNow may resist
backdating `sys_created_on` on insert; if so, write the true timestamps to
dedicated fields or keep the authoritative corpus as local CSV/parquet in
`data/eval/` and treat the PDI load as best-effort for the live-demo subset;
document the choice in an ADR). The eval harness and analytics read from the
authoritative corpus.

**Definition of done:** reproducible run from a clean clone; `pytest` green,
including new tests that assert each seeded pattern is statistically present
(e.g., the spike window's volume exceeds baseline; the degrading category's
monthly MTTR is monotonic-ish; cluster families exist); a notebook or script
that plots volume-over-time and MTTR-by-category for instructor eyeball
verification; ADR for the generator design; PR with all of the above.

## Schedule constraints (fixed — do not move)

Tue/Thu class. Sep 8 is the next session. A1 Sep 24 · A2 Oct 8 · A3 Oct 22 ·
A4 Nov 5 · A5 Nov 19 · A6 Dec 10. No class Nov 24/26. Finals-week capstone
demo. Six assignments × 100 pts = 75%; final = 25%.

## Working agreements for AI sessions in this repo

- Small PRs, one concern each; conform to existing file layout and naming.
- Run the generator and `pytest` before opening any PR; paste key output in
  the PR description.
- Never commit: `.env`, credentials, model artifacts >few MB (ADR first),
  or `seeded_truth_manifest.json`.
- When a decision has course-design implications (schedule, grading,
  assignment scope), stop and ask the instructor rather than deciding.
