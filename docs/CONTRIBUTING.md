# Contributing

This repository is a pre-registered benchmark, so contributions work differently from a normal codebase.

## Reporting an error in the results or scoring

Open an issue with the **Results or scoring error** template. Include the table row or `results/summary.csv` cell, what you believe is wrong, and how you checked (a command, a source URL, or a line of scoring code). Confirmed errors are fixed in the open: the correction goes in `docs/CHANGELOG.md` with a date and, if a score changes, the summary is rebuilt and the tables in RESULTS.md are regenerated (`python scripts/check_results.py --write`) and re-dated.

## Security problems and data concerns

Don't open an issue. Follow [SECURITY.md](../SECURITY.md).

## Changes to the method

The method is frozen at tag `v1.0-prereg` (see [PREREG.md](PREREG.md)). The frozen text gets editorial fixes only, each logged in `docs/CHANGELOG.md`. A change of method is a new version: it's proposed in an issue, logged in `docs/CHANGELOG.md` with a task version bump, and applies to new runs only.

## Adding a vendor or endpoint

New endpoints can be tested against the same 500 contacts and listed next to the original four. To add one:

1. **Write an adapter.** Follow `providers/clay.py`: one enrichment call per contact, the same three input fields (first name, last name, company domain), and retries only on 429, 5xx or no response (METHODOLOGY.md section 5). Shared helpers are in `providers/common.py`.
2. **Ask for the input file.** It names real people, so it isn't in the repo: open an issue titled "Data request" ([PRIVACY.md](PRIVACY.md) says how it's handled).
3. **Run it the same way.** One full run, the same verifiers (ZeroBounce for email, Twilio Lookup for mobiles) and the same scorers, using `benchkit` at the pinned commit. Vendors run it on their own account or give us a test key, and pay their own usage.
4. **Send the run folder** for audit (privately; it holds personal data). We re-score it with `scripts/reproduce.sh`, check it against the protocol, and log the attempt in [REPRODUCTIONS.md](REPRODUCTIONS.md).

A new endpoint is listed in RESULTS.md as a **later addition**, with its run date, separate from the four pre-registered endpoints. Vendor data changes over time, so it isn't ranked against runs from a different date. A vendor that ran it can choose to be named or listed anonymously.

## Code changes

Pull requests are welcome for bugs in the scoring code, the tests or the docs. Every pull request:

- runs the tests (`python -I -m unittest discover -s tests`) and the CI checks: no secrets, no personal data. Maintainers run `scripts/check_names.sh` before every push, which checks every commit for the real vendor names against a list kept outside the repository;
- needs a review from the code owners (`.github/CODEOWNERS`);
- changes no committed result unless it fixes a confirmed error, logged as above.

## Re-running the benchmark

See [REPRODUCE.md](REPRODUCE.md). Tell us how it went with the **Reproduction report** issue template, whether or not your numbers matched; attempts are logged in [REPRODUCTIONS.md](REPRODUCTIONS.md). If you publish your own run, please say which version of the method and of `benchkit` you used, and cite this repository (`CITATION.cff`).
