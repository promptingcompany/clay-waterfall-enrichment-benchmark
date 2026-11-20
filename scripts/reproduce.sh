#!/usr/bin/env bash
# One command to check this repository: tests, published numbers, anonymity and, when the private
# run folders are present, a re-score. Stops at the first failure. See docs/REPRODUCE.md.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt
PY=.venv/bin/python

echo "1/4 Tests"
"$PY" -I -m unittest discover -s tests
echo "2/4 Published numbers match results/summary.csv"
"$PY" scripts/check_results.py
echo "3/4 results/ holds no email addresses (vendor names: scripts/check_names.sh, with the private list)"
"$PY" bench check-anon

if [ -d private/runs ]; then
  echo "4/4 Re-score every run in private/runs and compare the rebuilt summary.csv with the committed one"
  # Work on a copy, so the run files that results/manifest.json hashes are never rewritten.
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  cp -R private "$tmp/private"
  for run in private/runs/*/; do
    BENCH_ROOT="$tmp" "$PY" bench score "$(basename "$run")" > /dev/null
  done
  BENCH_ROOT="$tmp" "$PY" bench summary > /dev/null
  diff results/summary.csv "$tmp/results/summary.csv"
  echo "    re-scored summary.csv is identical to the committed one"
else
  echo "4/4 Skipped: no private/runs folder, so nothing to re-score (docs/REPRODUCE.md, section A)"
fi
echo "All checks passed."
