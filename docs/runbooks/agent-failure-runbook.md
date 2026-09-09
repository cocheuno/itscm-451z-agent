# Runbook: agent failure
> Written in Module 9 (A4). Audience: a service-desk lead who has never read the code.

## Detection
| Signal | Where to look | Threshold |
|---|---|---|

## Degraded modes
- **read-only** — agent classifies and recommends; no writes.
- **propose-only** — agent writes proposals to the approval queue only.
- **human queue** — agent stops; new tickets route to the default human queue.

## Recovery

## Communication template
