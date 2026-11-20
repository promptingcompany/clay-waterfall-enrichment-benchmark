# Reproductions

A log of attempts to reproduce this benchmark: ours and anyone else's, whether they matched or not. To add yours, open a "Reproduction report" issue. We add a row and link the issue.

| Date | Who | What was run | Result | Link |
|---|---|---|---|---|
| 2026-11-19 | The Prompting Company (the authors, so not independent) | Offline re-score from the four private run folders, using the steps of `scripts/reproduce.sh`: the tests, `scripts/check_results.py`, `./bench check-anon`, then `./bench score` on a copy of every run and `./bench summary`. `./bench audit` was run as well. benchkit v0.1.3 code from a local checkout; the script's install step was skipped, because the machine was offline | Match. The rebuilt `results/summary.csv` is identical to the committed one, every re-scored run record is unchanged, and the audit passed | None |

No independent reproduction has been reported yet.
