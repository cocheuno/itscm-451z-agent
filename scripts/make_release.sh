#!/usr/bin/env bash
# Usage: scripts/make_release.sh v0.3 "Rung 3: governed writes"
set -euo pipefail
TAG="$1"; MSG="$2"
grep -q "\[$TAG\]" CHANGELOG.md || { echo "CHANGELOG.md has no section for $TAG"; exit 1; }
ruff check . && pytest -q && python -m eval.harness --rung auto --report "eval/reports/$TAG.json"
git tag -a "$TAG" -m "$MSG" && git push origin "$TAG"
echo "now create the GitHub Release for $TAG and attach eval/reports/$TAG.json"
