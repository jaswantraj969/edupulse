#!/usr/bin/env bash
# Runs the milestone gate and prints every command with its verbatim output.
# Usage: scripts/gate.sh [--e2e]    (exit code is non-zero if any check fails)
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATUS=0
export NO_COLOR=1 FORCE_COLOR=0

run() {
  local dir="$1"; shift
  echo "\$ (cd $dir && $*)"
  # Local paths are masked so the output can be committed to the review packet.
  (cd "$ROOT/$dir" && "$@") 2>&1 | python "$ROOT/scripts/sanitize_output.py"
  local code=${PIPESTATUS[0]}
  echo "[exit $code]"
  echo
  [ "$code" -eq 0 ] || STATUS=1
}

run backend uv run ruff check .
run backend uv run ruff format --check .
run backend uv run mypy app tests
run backend uv run pytest --cov --cov-report=term-missing -p no:cacheprovider

run ml uv run ruff check .
run ml uv run ruff format --check .
run ml uv run mypy edupulse_ml tests
run ml uv run pytest --cov -p no:cacheprovider

run frontend npm run lint
run frontend npm run typecheck
run frontend npm test
run frontend npm run build

if [ "${1:-}" = "--e2e" ]; then
  run frontend npx playwright test --reporter=list
fi

echo "GATE RESULT: $([ $STATUS -eq 0 ] && echo PASS || echo FAIL)"
exit $STATUS
