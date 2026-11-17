# ADR-0010: The incident workflow does not require an Anthropic key
- **Status:** Accepted
- **Date:** 2026-11-17
- **Rung/Module:** End-to-end incident workflow

## Context
`agent.config.load()` refused to start when `ANTHROPIC_API_KEY` was empty. The end-to-end tick does not call a model. It constructs the ServiceNow client from the orchestrator's incident user and passes `live=True` into `bind_writes`. `AGENT_MODE` stays `dry_run` unless that caller says otherwise.

## Decision
`load()` reads `ANTHROPIC_API_KEY` with a default of `""`. An empty key is allowed. Every other setting still uses `_env` and still refuses a missing value. A path that calls Anthropic has to set the key before it runs. The tick does not call `load()` or `from_env()`.

## Alternatives considered
- Keep the required key and put a dummy value in the orchestrator environment. That pretends an LLM call exists.
- Split `load()` into two functions. The one-line default is the smaller change.

## Consequences
The incident package can be imported and the eval harness can run without an Anthropic key. Incident text in this phase is not sent to an LLM. Category comes from the CI-class table. Similarity is a local term-count cosine.

## Action-tier impact
None. Tiers are unchanged.
