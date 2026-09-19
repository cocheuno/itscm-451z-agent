# Tuesday, Sep 15: "Make the agent see the data" (Rung 0 close-out)

About 75 minutes. Three parts, one PR at the end, then tag `v0.0`. This page is the checklist and rubric;
the step-by-step walkthrough with expected output is the [Module 2 lecture](../lectures/02-rung0-closeout.md).

## Where we are

At the end of Sep 8 you had a clone of this repository, a Python environment, and a `.env` pointed at your PDI
(`docs/setup.md`). Since then the instructor merged ten pull requests into `main`. You did not write them, but
you will use every one of them, so here is what changed and why:

| PRs | What landed | Why it matters today |
|---|---|---|
| 1, 2, 4 | `requirements.txt` gained pandas, scikit-learn, sentence-transformers, matplotlib, statsmodels, joblib | Part 3 needs pandas; Thursday needs scikit-learn |
| 3 | A deterministic synthetic corpus: `data/eval/incidents_history.csv` (4,242 closed incidents, Mar to Aug 2026), `incidents_open.csv` (150 open), `changes.csv` (6), the generator that made them, and ADR-0002 | Everything you analyse or train on comes from these files |
| 5 to 9 | `scripts/seed_pdi.py` learned what the PDI actually does: it refuses basic auth for interactive users, its close codes changed in Utah, it stamps every timestamp with the insert time, and closed incidents are read-only. All recorded in ADR-0002 | Part 1 is the service account this forced; Part 3 explains why you read the CSV and not the PDI |
| 10 | This handout, Thursday's, the `src/agent/analytics/` package, `notebooks/01_history_eda.py`, and an acceptance test for `list_all` | Your starting point for Parts 2 and 3 |

The pattern to notice: every change arrived as a feature branch, a pull request with the template filled in,
green CI, and a merge by the reviewer. Nothing went to `main` directly. That is the Git thread of the course,
and your PR today follows the same path. `git log --oneline --merges` shows the ten merges.

## Update your clone (do this first, about 10 minutes)

1. See what state your clone is in:

   ```
   git status
   git branch
   ```

   If `git status` lists modified files you want to keep, commit them on a branch first
   (`git checkout -b wip-sep08 && git add -A && git commit -m "WIP from Sep 8"`). `.env` is git-ignored and
   is never listed; leave it where it is.
2. Get onto `main` and pull:

   ```
   git checkout main
   git pull origin main
   git log --oneline -1
   ```

   The last command should print `5018b0f Merge pull request #11 ...` (or newer). If `git pull` complains
   about local changes, go back to step 1.

   **If the commit it prints is something else entirely** (for example `f5dd47c`) and `pytest -q` reports only
   6 tests, your clone is of an earlier copy of the project, not of `cocheuno/itscm-451z-agent` (the course
   repository was created on Sep 9). The histories are unrelated and a pull cannot join them. Re-clone, and
   keep the old folder only for its `.env`:

   ```
   cd ..
   git clone https://github.com/cocheuno/itscm-451z-agent.git
   cd itscm-451z-agent
   copy ..\<old-folder>\.env .env        # macOS/Linux: cp ../<old-folder>/.env .env
   python -m venv .venv
   ```

   then continue with step 3 in the new folder. Delete the old folder once you have copied anything you
   changed on Sep 8.
3. Install the new libraries into your virtual environment (activate it first: `.venv\Scripts\activate` on
   Windows, `source .venv/bin/activate` elsewhere):

   ```
   pip install -r requirements.txt
   pip install -e .
   ```

   `sentence-transformers` pulls in PyTorch, which is a large download (well over a gigabyte with GPU
   support). If it is slow or fails, install the CPU build first and re-run the line above:
   `pip install torch --index-url https://download.pytorch.org/whl/cpu`. You do not need it until Module 5.
4. Prove the clone is healthy:

   ```
   pytest -q
   ```

   Expect `44 passed, 1 skipped` (the skip is the pagination acceptance test you will turn green in Part 2).
   If the count is lower, `requirements.txt` did not fully install; read the first error.

Your PDI is still empty. Part 2 loads it. If you seeded it on Sep 8 with an older version of the script, run
`python scripts/reset_pdi.py` after Part 1 before seeding again; it only removes records the seeder created.

**Two rules for the whole course, starting now**

- `data/eval/incidents_open.csv` carries `gt_*` columns. They are grading ground truth. Never train on them,
  never look them up while classifying. Your eval numbers come from the harness, which uses them for you.
- `data/synthetic/patterns.yaml` is the answer key for the seeded patterns you will hunt for in later modules.
  Do not read it. If you open it by accident, say so in your next PR.

## Part 1: a service account on your PDI (20 min)

Your instance refuses REST basic auth for any user who can log in interactively (the syslog line is
`SNCRestrictBasicAuthUserAuthenticationGate`), so the agent needs a non-interactive account. This is the
least-privilege posture from `docs/governance/governance.md`: the agent is never `admin`.

1. In your PDI as admin, create a user `agent_svc`. Identity type **Machine**. Give it the roles `itil` and
   `itil_admin`. Set a password.
2. The user form hides the two flags that matter, so set them with a background script. Open
   `https://<your-instance>.service-now.com/sys.scripts.do`, paste, Run script:

   ```javascript
   var gr = new GlideRecord('sys_user');
   if (gr.get('user_name', 'agent_svc')) {
     gr.setValue('web_service_access_only', true);
     gr.setValue('internal_integration_user', true);
     gr.setValue('locked_out', false);
     gr.setValue('password_needs_reset', false);
     gr.update();
     gs.info('agent_svc: wsao=' + gr.getValue('web_service_access_only') +
             ' integration=' + gr.getValue('internal_integration_user'));
   } else {
     gs.info('agent_svc not found');
   }
   ```

   Expect `wsao=1 integration=1`.
3. Copy `.env.example` to `.env`, fill in your instance URL, `SN_USER=agent_svc`, and the password.
4. Prove it works. `python -m agent.config` prints ok, and this returns 200:

   ```
   python -c "from agent.servicenow.client import ServiceNowClient as C; print(C.from_env().list('incident', limit=1))"
   ```

   A 401 here means the flags did not take; re-run the script and read its output.

## Part 2: seed, paginate, poll (25 min)

1. `python scripts/seed_pdi.py` loads the 150 open tickets. Note the time; you need it as a watermark.
2. Finish `ServiceNowClient.list_all` in `src/agent/servicenow/client.py` (the `TODO(student)`): call `list`
   with increasing `offset` until a page comes back shorter than `page`. The acceptance test is already
   written and currently skips:

   ```
   pytest tests/test_client_pagination.py -v
   ```

   Make it pass.
3. Write three to five keyword rules in `RULES` in `src/agent/rung0_poller.py`. Order matters, first match
   wins. Pick keywords by reading twenty open tickets in your PDI, not by guessing.
4. Run the poller on what you just seeded, then score the rules on the holdout set:

   ```
   python -m agent.rung0_poller --since "<time you seeded>" --dry-run
   python -m eval.harness --rung 0
   ```

   Rung 0 will score well below the 0.80 `classification_accuracy` threshold. That is the point: Thursday
   replaces the rules with a model.

## Part 3: first look at the history (30 min)

Open `notebooks/01_history_eda.py` in VS Code. It is a notebook in cell format (`# %%` blocks) and runs as a
script too. Answer the four questions it poses over `data/eval/incidents_history.csv`:

1. volume by weekday
2. category mix, plus the top subcategories in the largest category (one cell is yours to write)
3. median resolve time by category and month
4. breach rate by priority

Then write five observations in the last cell. Each one names a number from a table. You will probably
notice things; do not chase them yet. Naming a pattern is not the same as measuring it, and A2 asks for the
measuring.

Why the CSV and not your PDI: the instance stamps every timestamp with the insert time, so the PDI copy of
the history has no usable dates (ADR-0002). Every history record in the PDI carries its corpus number in
`correlation_id`, which is the join key when you need both.

## Deliverable

One PR from branch `feature/rung0-closeout` with:

- `list_all` implemented, `tests/test_client_pagination.py` green
- three to five rules, and the harness table for `--rung 0` pasted into the PR description
- `notebooks/01_history_eda.py` with the four answers and five observations
- the PR template filled in: rung, what changed, eval results, ADRs touched (none), checklist

After the instructor merges: `git tag -a v0.0 -m "Rung 0: rules poller" && git push origin v0.0`.

## Rubric (checklist)

| Item | Meets | Partial | Missing |
|---|---|---|---|
| Service account | 200 from the one-liner, `.env` not committed | works only as admin | 401 |
| `list_all` | acceptance test passes; no duplicate or missing records | pages but off by one at the boundary | still `NotImplementedError` |
| Rules | 3 to 5 rules chosen from real ticket text, harness table in the PR | rules present, no harness run | fewer than 3 or untested |
| EDA | four tables correct, five observations each citing a number | tables correct, observations vague | cells not run |
| Git | branch, PR template filled, tag `v0.0` pushed after merge | PR without template or tag | work on `main` |
