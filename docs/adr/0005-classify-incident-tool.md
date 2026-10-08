@'
# ADR-0005: classify_incident as a read-tier tool
- **Status:** Accepted
- **Date:** 2026-10-07
- **Rung/Module:** Rung 1 / Module 4
- **Related Issue/PR:** #

## Context
The agent needs model inference as something it can call and audit, the same way it calls the ServiceNow read tools. Calling `predict.classify` directly from agent code would bypass the registry, so there would be no tier and no audit entry for the suggestion.

## Decision
Register `classify_incident` in `src/agent/tools/schemas/` at the read tier. It is served by `agent.analytics.predict.classify`, the currently selected local model. The LLM classifier stays in the bake-off and is not a tool.

## Alternatives considered
- Call `predict.classify` directly from the poller without a schema — rejected: no tier, no audit entry, violates "every number traceable to an audited tool call".
- Register the LLM classifier as the tool instead — rejected for now: slower, costs money per call, and the bake-off shows it less accurate on this corpus; the memo can revisit.

## Consequences
One audit entry per suggestion, tagged `classify_incident` with the model version. The suggestion is advisory: the description forbids stating it to a customer as fact or using it to set priority. The MCP server does not expose this tool; it is for the agent's own loop.

## Action-tier impact
Adds a read-tier tool. `docs/governance/governance.md` section 2 gains the row `classify_incident | read` in the same PR.
'@ | Set-Content -Encoding utf8 docs\adr\0005-classify-incident-tool.md