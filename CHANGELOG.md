# Changelog
All notable changes to this project are documented here. Format: Keep a Changelog. Versioning: one minor tag per rung.

## [Unreleased]
### Added
- Repository skeleton.
- Historical synthetic corpus generator with seeded truth (clusters, change spike, seasonality + trend,
  degrading MTTR, breach signal, poison bait); committed corpus under `data/eval/`; pattern-presence tests;
  instructor plot script; PDI seeder loads open set and closed history (ADR-0002).
- Analytics/ML dependencies (pandas, scikit-learn, sentence-transformers, matplotlib, statsmodels, joblib).
### Changed
- PDI history records carry their corpus number in `correlation_id`; the instance stamps all four timestamps on
  insert, so `data/eval/incidents_history.csv` is the only source of time for analytics (ADR-0002 findings).
  The seeder retries the dates with one PATCH and keeps patching only if the instance honours it; a refused
  PATCH (403 ACL on closed incidents) is reported and the load continues.
### Fixed
- `ServiceNowClient._request` no longer tries to parse JSON from a `204 No Content` (or empty) body, so
  `scripts/reset_pdi.py` survives its first DELETE instead of crashing with `JSONDecodeError`.
