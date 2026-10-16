#!/usr/bin/env bash
# Runs every check for this project, in order. Stops at the first failure.
# Claude runs this after each change (see ../CLAUDE.md, "Work loop").
#
# Each step is "run_step <label> <command>" so a label cannot be counted
# without its command. A command that needs a pipe or quotes goes in a
# function: f() { ...; }; run_step <label> f
# If no step is configured, this script FAILS on purpose. "No checks" is not
# the same as "checks passed".

set -euo pipefail
cd "$(dirname "$0")/.."

# run_step <label> <command...>
# Prints the label, runs the command, and counts it only when the command ran.
STEPS_RUN=0
run_step() {
  local label="$1"; shift
  echo; echo "== $label"
  "$@"
  STEPS_RUN=$((STEPS_RUN + 1))
}

# --- Checks ---------------------------------------------------------------

# Dependency import check, taken from app/run.bat and app/run_qa.bat.
# The project has no test, lint or typecheck command yet (adopted 2026-10-16).
smoke() { (cd app && python -I -c "import uvicorn, fastapi, openpyxl"); }
run_step smoke smoke

# Project with a UI: KRDS conformance score. Fill the script name and the
# threshold from dev/.claude/skills/krds-improve after it is installed.
# run_step krds      <krds score script> --min-score 90

# ------------------------------------------------------------------------

if [ "$STEPS_RUN" -eq 0 ]; then
  echo
  echo "FAIL: No checks configured. Add at least one step to scripts/check.sh."
  exit 1
fi

echo
echo "All $STEPS_RUN checks passed."
