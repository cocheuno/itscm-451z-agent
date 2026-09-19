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

## Synthetic data: the historical corpus and the PDI

The authoritative operational data is a deterministic synthetic corpus committed under `data/eval/`:
about 4,200 closed incidents (2026-03-01 to 2026-08-31), 150 open tickets, and six change records.
Analytics and the eval harness read these files; the PDI is loaded from them (ADR-0002).

```bash
python data/synthetic/generate_tickets.py --dry-run   # statistics only
python data/synthetic/generate_tickets.py             # regenerate data/eval/*.csv (byte-identical from a clean clone)
python scripts/plot_seeded_patterns.py                # eyeball check -> eval/reports/seeded_patterns.png
```

The generator also writes `seeded_truth_manifest.json` (instructor-only, gitignored) outside the repo,
by default to `~/.itscm451z/`. Never commit it.

The PDI refuses REST basic auth for interactive users, so `.env` must name a non-interactive service account
(see `.env.example` and ADR-0002).

```bash
python scripts/seed_pdi.py              # open set -> PDI; ground truth -> data/synthetic/ground_truth.csv
python scripts/seed_pdi.py --history    # closed history; the PDI stamps its timestamps, so join
                                        # correlation_id to data/eval/incidents_history.csv (ADR-0002)
python scripts/seed_pdi.py --history --resume   # continue an interrupted history load (about 20 minutes in full)
python scripts/seed_pdi.py --changes    # change records
python scripts/seed_pdi.py --attacks    # instructor only: red-team tickets
python scripts/reset_pdi.py             # removes everything the seeder created
```

## Lectures and in-class exercises

Lecture notes under `docs/lectures/` are complete walkthroughs (why, every step, expected output); the handouts
under `docs/exercises/` are the checklists and rubrics. Each session ends in a PR. The Rung 1 scaffolding lives in
`src/agent/analytics/` (features, train, predict) and `notebooks/`.

## Run the eval harness

```bash
python -m eval.harness --rung 1          # dry run against the 40-ticket holdout (data/eval/eval_set.jsonl)
```

## Repository layout

See `docs/setup.md` for the environment guide and `CONTRIBUTING.md` for the submission process.
Every significant decision has an ADR in `docs/adr/`.

## Non-negotiables
1. Every agent action is logged (inputs, reasoning, tool calls, outcome).
2. Every tool declares an action tier: `read` / `propose` / `execute_with_approval` / `autonomous`. Tiers are enforced in `agent/tools/registry.py`, never in a prompt.
3. The eval set runs on every PR.
4. An ADR for every significant decision.
