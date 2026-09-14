# ADR-0002: Historical synthetic corpus with seeded truth; local CSV is authoritative, PDI load is best effort
- **Status:** Accepted
- **Date:** 2026-09-09
- **Rung/Module:** Module 2 tooling for the analytics thread (A2, A3, A4, M11, A5, M13)
- **Related Issue/PR:** PR "historical-data-generator"

## Context
The analytics thread needs about six months of closed incidents with structure the student can later recover:
five latent problem clusters (M13), a change-caused spike (A3), weekly seasonality plus trend (M11), a category
whose MTTR degrades (A2), a learnable-but-imperfect SLA-breach signal (A4) and a few poisoning-bait tickets (A5).
The instructor grades the student's analytics against a manifest of what was planted, so the manifest must not
be committed while the generator and its configuration must be, and a clean clone must reproduce the corpus.

Forces: CI runs offline with no PDI credentials or API keys; the corpus must be reproducible byte for byte;
ServiceNow protects system fields, so historical timestamps may not survive an insert; the text must vary
enough that clustering is a real exercise, without calling an LLM; the PDI is a single hibernating developer
instance that will not enjoy 4,000 inserts on every reseed.

## Decision
1. **Two config files.** `data/synthetic/taxonomy.yaml` describes the world (categories, groups, priority
   matrix, volume shares, resolution baselines, phrase banks). `data/synthetic/patterns.yaml` describes what is
   hidden in it (seed, window, seasonality, trend, clusters, spike, degrading category, breach coefficients,
   poison bait). The manifest is patterns.yaml plus the resolved ticket numbers, so patterns.yaml being readable
   is accepted: the graded deliverable is the method that recovers the structure, not knowing it exists.
2. **Offline, deterministic paraphrase.** Each cluster (and the spike family, and every background subcategory)
   has a small compositional grammar: symptom, context and artifact phrase banks combined through shared sentence
   frames, then word-level synonym substitution, optional openers, irrelevant details, a multilingual prefix and
   dropped-letter typos, all drawn from one `random.Random(seed)`. Short descriptions are kept unique. The
   root cause is never named; the CI is visible on only ~30% of a family. No LLM and no network are involved,
   so CI can regenerate the corpus and the output is stable across Python 3.11 and 3.12 (verified).
3. **Breach signal by construction.** Each ticket gets a logit over priority, category, assignment-group load at
   open time (computed from the corpus itself in time order), off-hours and weekend, plus Gaussian noise; breach
   is a Bernoulli draw. Resolution time is then drawn on the correct side of the SLA target, so `made_sla` and
   `resolve_minutes` never contradict each other. The coefficients and noise were tuned so five-fold logistic
   regression lands at AUC ~0.80 on the default seed (test asserts the 0.75-0.85 window). The degrading category
   scales its met-side resolution times by `1 + 0.6 x month`, with a softened effect on breached durations.
4. **The corpus lives in the repo; the manifest never does.** `data/eval/incidents_history.csv` (~4,200 closed),
   `incidents_open.csv` (150 open, with ground-truth columns for the rung-0/1 harness) and `changes.csv` are
   committed (about 1.5 MB) and are the authoritative input for the eval harness and every analytics module.
   The generator writes `seeded_truth_manifest.json` to `~/.itscm451z/` by default, refuses any in-repo path
   that git does not ignore, and the file name is gitignored as a second guard. Because generation is
   deterministic, the instructor regenerates the manifest locally; the PR records its digest for comparison.
5. **PDI load is best effort and secondary.** `scripts/seed_pdi.py` always loads the open set (no category, so
   the classifier has work to do) and loads the closed history only with `--history`. History rows carry their
   true timestamps in `opened_at`, `resolved_at` and `closed_at`, which are ordinary writable datetime fields.
   `sys_created_on` is also sent as a probe, and the seeder reads the first record back and prints which fields
   the instance honoured. Analytics and the harness key on `opened_at`, never on `sys_created_on`.

## Investigation: can `sys_created_on` be set on insert?
`sys_created_on` is a platform-maintained system field. Server-side, GlideRecord can preserve or set it only
after `autoSysFields(false)`, and import-set transform maps can map into it; the community threads on this are
consistent that outside those paths the platform stamps the field at insert. The REST Table API exposes no
equivalent switch, so a POST that includes `sys_created_on` is expected to be overwritten with the insert time
(some instance versions accept it when the caller has admin and the field is not marked read-only, which is why
the seeder probes rather than assumes). This could not be verified against the course PDI from the CI-style
environment used for this work (no `.env`, no network to the instance); the probe output from the first
`--history` run should be pasted into this ADR. Sources reviewed: ServiceNow Community, "Possible to set/update
sys_created_on and sys_created_by fields"; "Can I update sys_created_on field value"; "Transform map to update
sys_created_on"; LearnITbyPrashant, "Stealth modify data with setWorkflow() & autoSysFields()".

Consequence for the course: the rung-0 poller's `sys_created_on` watermark remains correct for tickets inserted
live (the open set and anything the student creates), while every historical analysis uses `opened_at`. If the
probe shows the field was honoured, nothing changes; the CSV is still authoritative.

## Findings from the first PDI load (2026-09-14, instance dev406825)
- **Basic auth is gated.** The instance logs `SNCRestrictBasicAuthUserAuthenticationGate: denied basic-auth API
  call for interactive-login user [...] under enforce=true` and answers 401 for `admin` and for any user that can
  log in interactively. The agent therefore runs as a dedicated service account `agent_svc` with
  `web_service_access_only` and `internal_integration_user` set (the user form in this release hides the flags;
  a background script sets them), identity type Machine, roles `itil` + `itil_admin`. `.env.example` reflects
  this. It is also the least-privilege posture the governance document assumes; `admin` is never granted.
- **Close codes differ by release.** The incident data policy makes "Resolution code" mandatory on closed
  records, and the instance blanks any `close_code` value it does not know. The corpus keeps the legacy labels
  ("Solved (Permanently)" and friends) because it is authoritative and release-independent; `seed_pdi.py` reads
  `incident.close_code` from `sys_choice` at load time and maps onto the live list, falling back to the
  post-Utah defaults ("Solution provided", "Workaround provided", "No resolution provided").
- **Open set and history are separate targets** (`--open`, `--history`, `--changes`) so a history run never
  re-inserts the 150 open tickets; the first attempt did, and `reset_pdi.py` was needed before retrying.
- **`sys_created_on` probe:** pending; the first successful `--history` run prints the sent-versus-stored table,
  to be pasted here.

## Alternatives considered
- LLM-paraphrased cluster text: better prose, but non-deterministic, needs an API key in CI, and costs money on
  every regeneration. Rejected; the compositional grammar is enough to defeat exact-match clustering.
- Parquet for the corpus: smaller, typed, but adds pyarrow and is not diff-able in review. CSV at 1.5 MB is fine.
- Generating the corpus in CI instead of committing it: reproducible, but then the student's analytics, the
  manifest and the PDI could silently drift after a config edit. Committing plus a test that regeneration matches
  the committed files gives both.
- Committing an encrypted manifest: solves nothing the gitignore plus the default path outside the repo do not,
  and adds key handling.
- Making the PDI the authoritative store: backdating is uncertain, reseeding is slow, and CI has no access.

## Consequences
Positive: reproducible corpus and manifest from one command; every seeded pattern has a test; offline CI.
Negative: patterns.yaml reveals which patterns exist (not which tickets); the corpus adds 1.5 MB to the repo;
the breach signal is only guaranteed in the AUC window at the default seed (other seeds are close but untested).
Monitor: if anyone edits taxonomy.yaml or patterns.yaml, `pytest` fails until `data/eval` is regenerated and the
instructor's manifest is regenerated too, which is the intended coupling. The SLA targets copied into
patterns.yaml are asserted equal to `agent/workflow/sla.py`; changing the SLA later means a deliberate corpus
regeneration.

## Action-tier impact
None. The generator writes files; the seeder is pre-existing instructor tooling that writes to the PDI outside
the agent and its tool registry. No agent tool or tier changes.
