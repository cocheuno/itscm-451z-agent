# Module 2: "Make the program see the data" (Rung 0 close-out)

About 75 minutes. Three parts, a commit and a tag at the end, and your first journal page. This page is the
checklist and rubric; the step-by-step walkthrough with every command and what it should print is the
[Module 2 lecture](../lectures/02-rung0-closeout.md). If any word here is new, it is explained in
[Getting started](../lectures/00-getting-started.md).

## Before class

- A fresh clone with the virtual environment installed, per Getting started. Proof: `python -m pytest -q`
  ends in `passed` with `1 skipped`.
- `.env` filled in with your PDI address, `agent_svc`, and its password. Proof: `python -m agent.config`
  prints `config ok`.
- On a new branch: `git checkout main`, `git pull origin main`, `git checkout -b module-02`.

## Part 1: service account (20 min)

- [ ] `agent_svc` exists in your PDI with roles `itil` and `itil_admin`.
- [ ] The background script printed `wsao=1 integration=1`.
- [ ] The one-line Python check printed `[]` or a record, not `401`.

## Part 2: load, page, rule, poll, score (25 min)

- [ ] `python scripts\seed_pdi.py` printed `seeded 150 open tickets`. Seeding time written down, in UTC.
- [ ] `list_all` written; `python -m pytest tests\test_client_pagination.py -v` prints `PASSED`.
- [ ] Three to five rules chosen from twenty real ticket descriptions, `vpn` still first;
      `python -m pytest tests\test_rules.py -v` prints two `PASSED`.
- [ ] Poller run with your UTC watermark; `logs\audit.jsonl` has one new line per ticket.
- [ ] `python -m eval.harness --rung 0` run; the table copied for the journal.

## Part 3: first look at the history (30 min)

- [ ] Four cells run; the numbers match the lecture (1,153 Monday tickets; Inquiry / Help 0.288;
      Hardware median rising 640 to 2,799; P1 breach rate 0.617).
- [ ] The top-three-subcategories cell written and run.
- [ ] Five observations written, each naming a number.

## Deliverable

- [ ] `docs\journal\module-02.md` written with the four headings from the lecture.
- [ ] `git status` shows only the four files to be added; nothing from `.env`, `logs`, or the two
      git-ignored data files.
- [ ] One commit on `module-02` with the lecture's message; tag `v0.0`; `git log --oneline -3` shows both.

## Rubric

| Item | Meets | Partial | Missing |
|---|---|---|---|
| Service account | Python check returns a list; `.env` not in git | works only as admin | 401 |
| `list_all` | pagination test passes; no duplicate or missing records | pages but off by one at the boundary | still `NotImplementedError` |
| Rules | 3 to 5 rules from real ticket text; harness table in the journal | rules present, no harness run | fewer than 3 or untested |
| EDA | four tables correct; five observations each citing a number | tables correct, observations vague | cells not run |
| Git | work on `module-02`, one commit, tag `v0.0`, journal present | commit without tag or journal | work on `main` or nothing committed |
