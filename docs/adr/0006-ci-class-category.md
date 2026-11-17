# ADR-0006: Category comes from the CI class, and this PDI's priority wins
- **Status:** Accepted
- **Date:** 2026-11-17
- **Rung/Module:** End-to-end incident workflow

## Context
The committed model `category-v0.2` scored 0.5 on the ten end-to-end arrival fixtures. Three wrong answers were above 0.99 confidence. A constant category was rejected. The course priority matrix maps impact 3 and urgency 3 to priority 5. On this PDI the data lookup `dl_u_priority` stores that pair as priority 4. The course routing table names groups that are not in the change world.

## Decision
Triage does not call the model. Category is a table keyed by CI class, supplied by the orchestrator: `cmdb_ci_appl` is `software` and `cmdb_ci_linux_server` is `hardware`. An unknown class gets no category. Priority uses `workflow/sla.py`, and the pair (3, 3) returns 4 so the value written by the platform is the value the workflow expects. The assignment group is the change-world service group of the incident's CI. The model file stays in the repository and is not used for this decision.

## Alternatives considered
- Keep the model — the scored accuracy is not good enough, and retraining was not approved.
- A single constant category — rejected. The two CI classes in this world are not the same category.
- Write priority 5 — a rules-on update of impact 3 and urgency 3 stores 4. The PDI wins.

## Consequences
The course matrix is unchanged, so the eval harness still scores priority from `sla.priority`. The end-to-end path uses `priority_on_this_pdi`. A new CI class needs a row in the orchestrator's table before triage will set a category.

## Action-tier impact
Adds `record_triage` at `execute_with_approval`. `docs/governance/governance.md` lists it.
