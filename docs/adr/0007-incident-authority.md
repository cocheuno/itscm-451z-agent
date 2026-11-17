# ADR-0007: The incident authority is an agent approver
- **Status:** Accepted
- **Date:** 2026-11-17
- **Rung/Module:** End-to-end incident workflow

## Context
Write tools stay on `execute_with_approval`. No tool is moved to the autonomous tier. A person is not sitting in the loop for these deterministic incident writes. The approval queue still requires a named approver, and an approval is valid only for one tool and one set of arguments, once.

## Decision
The incident authority approves a proposal when its tool and arguments are exactly the rule's decision. The approver recorded on the proposal is `incident authority`. The authority rejects any other arguments. The registry still refuses a later call whose arguments differ from the approved proposal and records that call as harmful. `AGENT_MODE=live` is not set in this repository. The end-to-end run passes `live=True` into `bind_writes` for that run alone.

## Alternatives considered
- A human approves each incident — too slow for the scripted arrivals, and the decision is a table lookup.
- The autonomous tier — rejected. An approval must still exist and be spent once.
- Trust the model's arguments — there is no model call on this path.

## Consequences
Every executed write has an approval id in the audit log. A test dispatches arguments that differ from the approved proposal and expects a harmful refusal. Real runs keep `harmful_action_count` at 0.

## Action-tier impact
No tier changes on the course tools. `record_triage`, `apply_known_error`, and `restore_service` are `execute_with_approval` with approver `incident authority`. `add_comment` stays `propose`; the workaround comment is a field on `apply_known_error`, which does execute.
