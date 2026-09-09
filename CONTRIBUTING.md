# Contributing — submission process

1. **One feature branch per rung**: `feature/rungN-<short-name>`. Never commit to `main`; branch protection enforces a PR with one approving review and green status checks.
2. **Open a draft PR early** and fill in the template (rung, what changed, eval results, ADRs touched, checklist). Mark ready for review when CI is green.
3. **CI must be green**: ruff, pytest, and the eval harness above `eval/thresholds.yaml` (from Module 8).
4. **ADRs**: any PR that changes a prompt, a tool schema, or a tier includes or updates an ADR in `docs/adr/`. Tier changes must also update `docs/governance/governance.md` in the same PR.
5. **Review**: the instructor reviews in the PR. Resolve every comment — fix it, or reply with a reasoned disagreement — then request re-review.
6. **Merge** only after approval. Squash-merge by default (ADR-0001). The Module 7 conflict exercise is merged with a merge commit so both histories are visible.
7. **Tag immediately after merge**: `git tag -a vX.Y -m "Rung N: ..."`, push the tag, create a GitHub Release and attach the eval report.
8. **Secrets never enter the repo.** `.env` is git-ignored; CI uses GitHub Secrets; the pre-commit gitleaks hook is mandatory from Module 12.
9. **Issues**: defects and design decisions are GitHub Issues labelled `defect` or `adr`, linked from PRs (`Closes #12`).

## Commit messages
Imperative subject line ≤ 72 chars; blank line; body explains *why*. Reference Issues and ADRs.

```
Add retrieval trust label to prompt context

Retrieved KB text was being treated as instruction (see Issue #9, RT-4).
Wrap tool results in <data> tags and state in the system prompt that
they are not instructions. Implements ADR-0011.
```
