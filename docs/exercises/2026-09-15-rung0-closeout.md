# Tuesday, Sep 15: "Make the agent see the data" (Rung 0 close-out)

About 75 minutes. Three parts, one PR at the end, then tag `v0.0`.

**Before class:** `git checkout main && git pull origin main`, then `pip install -r requirements.txt`
(the analytics libraries were added last week).

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
