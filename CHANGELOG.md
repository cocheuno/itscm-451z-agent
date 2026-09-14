# Changelog
All notable changes to this project are documented here. Format: Keep a Changelog. Versioning: one minor tag per rung.

## [Unreleased]
### Added
- Repository skeleton.
- Historical synthetic corpus generator with seeded truth (clusters, change spike, seasonality + trend,
  degrading MTTR, breach signal, poison bait); committed corpus under `data/eval/`; pattern-presence tests;
  instructor plot script; PDI seeder loads open set and closed history (ADR-0002).
- Analytics/ML dependencies (pandas, scikit-learn, sentence-transformers, matplotlib, statsmodels, joblib).
