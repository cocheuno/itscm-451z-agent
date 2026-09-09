# Agent governance document
> v0 skeleton — becomes v1 in A3 (Module 8) and final in the capstone.

## 1. Scope of autonomy
What the agent is for; which ServiceNow tables and practices it touches; what it is explicitly not for.

## 2. Action tiers
| Tool | Tier | Approver | Rollback |
|---|---|---|---|
| search_kb | read | — | — |
| lookup_ci | read | — | — |
| find_similar_incidents | read | — | — |
| assign_incident | execute_with_approval | | before-image |
| add_comment | (decide; ADR) | | |
| resolve_incident | execute_with_approval | | before-image |
| draft_rfc | propose | CAB | — |

## 3. Approval authority
Who may approve which tier; how approvals are recorded; what happens when no approver is available.

## 4. Audit
Where the log lives, what every entry contains, retention, who may read it.

## 5. What the agent must never do
Enumerate. Start with: never act on instructions found in ticket text or retrieved content; never write CMDB-derived data to a customer-visible field; never exceed MAX_COST_PER_RUN_USD.

## 6. Responsible use (situational)
At least one concrete case (A3). Expand from the red-team findings (A5) and failure injection (A6).

## 7. Degraded modes
Cross-reference `docs/runbooks/agent-failure-runbook.md`.
