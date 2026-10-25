#!/usr/bin/env bash
# Audit all dependency lock files for known vulnerabilities (pip-audit + npm audit).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
for project in backend ml; do
  echo "== pip-audit: $project"
  (cd "$ROOT/$project" && uv export --frozen --format requirements-txt --all-groups --no-emit-project -o "$TMP/$project.txt" >/dev/null)
  (cd "$ROOT/backend" && uv run pip-audit -r "$TMP/$project.txt" --strict --progress-spinner off)
done
echo "== npm audit: frontend"
(cd "$ROOT/frontend" && npm audit)
