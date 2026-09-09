# itscm451z-agent

AI agent that executes IT service management processes against a ServiceNow Personal Developer Instance.
Built rung by rung in ITSCM 451Z (UW–Whitewater, Fall 2026).

| Rung | Capability | Tag |
|---|---|---|
| 0 | Deterministic poller with rules | — |
| 1 | LLM classification + priority, eval harness | v0.1 |
| 2 | Read-only triage agent (KB, CMDB, similar incidents) | v0.2 |
| 3 | Governed write actions (tiers, approvals, audit, rollback) | v0.3 |
| 4 | Service-request workflow state machine + SLA timers | v0.4 |
| — | Threat model and hardened agent | v0.5 |
| 5 | Problem/Change: clustering, RFC drafting, CAB | v0.6 |
| 6 | Observability, failure injection | v1.0-rc1 |
| Final | Capstone | v1.0 |

## Setup from a clean clone

```bash
git clone git@github.com:<you>/itscm451z-agent.git
cd itscm451z-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in values; .env is git-ignored
python -m agent.config    # prints "config ok"
pytest
```

## Seed the PDI with synthetic tickets

```bash
python scripts/seed_pdi.py              # ~300 tickets with ground truth -> data/synthetic/ground_truth.csv
python scripts/seed_pdi.py --attacks    # instructor only: red-team tickets
python scripts/reset_pdi.py             # removes everything the seeder created
```

## Run the eval harness

```bash
python -m eval.harness --rung 1          # dry run against eval/eval_set.jsonl
```

## Repository layout

See `docs/setup.md` for the environment guide and `CONTRIBUTING.md` for the submission process.
Every significant decision has an ADR in `docs/adr/`.

## Non-negotiables
1. Every agent action is logged (inputs, reasoning, tool calls, outcome).
2. Every tool declares an action tier: `read` / `propose` / `execute_with_approval` / `autonomous`. Tiers are enforced in `agent/tools/registry.py`, never in a prompt.
3. The eval set runs on every PR.
4. An ADR for every significant decision.
