# ADR-0001: Record architecture decisions; squash-merge by default
- **Status:** Accepted
- **Date:** 2026-09-03
- **Rung/Module:** Module 1

## Context
The agent's design will change every week. Decisions about prompts, tiers, retrieval, and recovery need a durable, reviewable record that survives the people who made them.

## Decision
Every significant design decision is recorded as an ADR in `docs/adr/` using `0000-template.md`, numbered sequentially, and linked from the PR that implements it. PRs are squash-merged so that `main` has one commit per rung; the Module 7 conflict exercise uses a merge commit so that both histories are visible for the competency checklist.

## Alternatives considered
- Decisions in PR descriptions only — lost once the PR scrolls away.
- Merge commits everywhere — noisier `main`, harder to map commits to rungs.

## Consequences
ADR discipline is graded in every rubric. `git log main` reads as the rung history.

## Action-tier impact
None.
