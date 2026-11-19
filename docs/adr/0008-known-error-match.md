# ADR-0008: Known-error match uses the article source and the CI
- **Status:** Accepted
- **Date:** 2026-11-17
- **Rung/Module:** End-to-end incident workflow

## Context
The problem field that points at a primary known-error article queues a script action whose incident query matches every incident on this PDI. That field is not written. Close code `Known error` is refused with HTTP 403. `sn_incident_write` can update an incident and can read an assignment group. That role alone cannot read `kb_knowledge` or `problem`. `problem_task_analyst` is the role that can read both the published known-error article and the problem it points at.

## Decision
A match is a published `kb_knowledge` row whose short description starts with `E2E-`, whose `cmdb_ci` is the incident's CI, and whose `source` is a problem with `known_error` true and a non-empty workaround. Term-count cosine similarity of the incident text and the article text must clear the fixture midpoint. The E01 pair scores about 0.516. A printer decoy scores about 0.328, which is above 0.20, so the threshold is the midpoint of those two scores, about 0.422. The prefix on the article short description changed from the earlier marker. The scored body is the same fixture text. The midpoint was fixed from those two fixtures before the rerun and is not retuned from the instance. Markup in a stored article is stripped before the count, so the score uses the same words as the fixture. On a match the incident comment is the problem's workaround, `parent` is that problem, and the incident is resolved with close code `Workaround provided`. Close notes name the article number and the problem number. No knowledge-to-task row is inserted.

## Alternatives considered
- Read the primary article field — that is the write that walks every incident. It is not read and not written.
- Close code `Known error` — the platform refuses it.
- Similarity only, without the CI — the checkout cluster uses the same log-rotation words and must not take the CDN article.

## Consequences
The incident user reads the article and the problem and passes them into the pure match. The incident client writes the incident. Admin is not used on the tick. A unit test locks the midpoint threshold against the fixture pair and a printer decoy.

## Action-tier impact
Adds `apply_known_error` at `execute_with_approval`. See `docs/governance/governance.md`.
