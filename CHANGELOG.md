# Changelog
All notable changes to this project are documented here. Format: Keep a Changelog. Versioning: one minor tag per rung.

## [Unreleased]
### Added
- Repository skeleton.
- Historical synthetic corpus generator with seeded truth (clusters, change spike, seasonality + trend,
  degrading MTTR, breach signal, poison bait); committed corpus under `data/eval/`; pattern-presence tests;
  instructor plot script; PDI seeder loads open set and closed history (ADR-0002).
- Analytics/ML dependencies (pandas, scikit-learn, sentence-transformers, matplotlib, statsmodels, joblib).
- Rung 1 scaffolding: `src/agent/analytics/` (`features.py` with the time split, `train.py` with the model-card
  and artifact plumbing around a `TODO(student)` pipeline, `predict.py`), harness dispatch for rung 1, an EDA
  starter notebook, a pagination acceptance test, and handouts for the Sep 15 and Sep 17 sessions under
  `docs/exercises/`.
- Module 3 lecture notes (`docs/lectures/03-sla-rung1-eval-prs.md`): SLAs and customer communication, Rung 1
  classification versus the priority rule, the eval set and ground truth, feature branches and PRs.
- Lectures rewritten as complete walkthroughs (`docs/lectures/`): Module 2 close-out, Module 3, and the two
  Module 4 sessions (gradient boosting and the LLM classifier; the bake-off, memo and v0.1).
- Rung 1 scaffolding for the bake-off: `scripts/bakeoff.py` (one comparison table over the eval set),
  `agent.analytics.llm_classify` (raw-HTTP Anthropic classifier with schema-enforced labels and per-call cost),
  `train.py --pipeline lr|gbm`, `CATEGORY_MODEL_VERSION` pin in `predict`, and the harness joining ticket inputs
  (impact, urgency, short_description) into the eval rows so `priority_sla_agreement` can be met.
- Module 5 scaffolding and lectures: knowledge articles and CMDB items for the PDI (`seed_pdi.py --groups --cis
  --kb`), the three read-tier tools (`agent.tools.readonly`), an MCP server over the registry (`agent.mcp_server`,
  `mcp>=2.2`), a stdio client check, lectures 05a and 05b, and instructor implementation notes for Modules 3 to 5.
### Changed
- PDI history records carry their corpus number in `correlation_id`; the instance stamps all four timestamps on
  insert, so `data/eval/incidents_history.csv` is the only source of time for analytics (ADR-0002 findings).
  The seeder retries the dates with one PATCH and keeps patching only if the instance honours it; a refused
  PATCH (403 ACL on closed incidents) is reported and the load continues.
- `seed_pdi.py --history --resume` skips rows already in the PDI (by `correlation_id`) and appends to the map;
  the history load prints a progress line with an ETA every 100 rows.
### Fixed
- `ServiceNowClient._request` no longer tries to parse JSON from a `204 No Content` (or empty) body, so
  `scripts/reset_pdi.py` survives its first DELETE instead of crashing with `JSONDecodeError`.
