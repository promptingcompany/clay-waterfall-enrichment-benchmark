#!/usr/bin/env bash
# Checks every commit (files and messages) for the real names behind the anonymized providers.
# The names live in a gitignored file, so they never reach GitHub. Run before every push.
set -euo pipefail
f=${1:-private/anon-terms.txt}
[ -s "$f" ] || { echo "missing $f: one name or identifying term per line" >&2; exit 2; }
terms=$(mktemp); trap 'rm -f "$terms"' EXIT
grep -v '^[[:space:]]*$' "$f" > "$terms"
# grep exits 1 for no match; 0 (a match) or 2 (an error) must both fail.
rc=0; git grep -niF -f "$terms" $(git rev-list --all) || rc=$?
[ "$rc" -eq 1 ] || { echo "anonymized names found above, or git grep failed ($rc)" >&2; exit 1; }
rc=0; git log --all --format="%H %B" | grep -niF -f "$terms" || rc=$?
[ "$rc" -eq 1 ] || { echo "anonymized names found in a commit message above, or grep failed ($rc)" >&2; exit 1; }
echo "no anonymized names in any commit"
