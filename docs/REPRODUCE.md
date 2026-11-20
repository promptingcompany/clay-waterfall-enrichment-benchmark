# Reproducing this benchmark

This guide is for someone with no prior context: a person or an AI agent starting from a fresh clone. It covers two goals:

1. **Check our published results** against our run files (section A).
2. **Re-run the benchmark yourself** with the same method on a fresh sample (section B).

**What can't be reproduced exactly, by design.** The 500-contact input contains people's names and is never published, and vendor databases change daily. A re-run measures the same things the same way, on your own sample, but won't match our numbers row for row.

## What you get in this repo

| Published | Not published |
|---|---|
| Method (`METHODOLOGY.md`, frozen at `v1.0-prereg`; see docs/PREREG.md), task spec (`tasks/W1-v1.md`), scoring code (`scoring/`), Clay adapter (`providers/clay.py`), config (`config/bench.json`), industry map and non-personal firmographic key rows (`datasets/`), results (`results/`) | The input file and answer keys (personal data), run folders and raw vendor responses, the two competitors' names, prices and adapters (`private/`) |

## Requirements

- Python 3.10 or later (CI uses the version in `.python-version`), git, and network access to GitHub.
- The shared harness, `benchkit`, pinned in `requirements.txt` by commit (`4bf7520b766ee463813a06d1fee347b6d86c0423`, tag `v0.1.3`; published scores computed at benchkit v0.1.0; scoring unchanged since).
- For section B only: the accounts in the table below.

## Setup (both goals)

```bash
git clone https://github.com/promptingcompany/clay-waterfall-enrichment-benchmark.git
cd clay-waterfall-enrichment-benchmark
scripts/reproduce.sh
source .venv/bin/activate
```

`scripts/reproduce.sh` is the first step for both goals. It creates `.venv` if it's missing, installs `requirements.txt`, then runs the tests, the published-numbers check (`scripts/check_results.py`) and the check that `results/` holds no email addresses (`./bench check-anon`), and prints what it checked. If `private/runs/` exists it also re-scores every run and fails if the rebuilt `results/summary.csv` differs from the committed one (section A, step 3). It stops at the first failure.

`./bench` uses the installed `benchkit`. If it isn't installed, it falls back to a `benchkit` checkout next to this repo (`../benchkit`, at tag `v0.1.3`).

Check the pre-registration:

`docs/PREREG.md` gives the pre-registration commit and the SHA-256 of every frozen file. This repository was published without its working history, so the commit itself is in a private archive; docs/PREREG.md says how to get read access and check it.

Each change after the tag is logged with its date in `docs/CHANGELOG.md`.

## A. Check our published results

Without our private run files you can:

1. **Read the results:** `results/summary.csv` (one row per endpoint, with every segment cut) and the tables in `RESULTS.md`, which are generated from it (`python3 scripts/check_results.py` confirms they match).
2. **Confirm the run plan:** `results/run-plan.json` holds the config hash, the input file's SHA-256, the price date and the anonymity overlay's hash. It was frozen before the runs and re-frozen once afterwards to add Provider A's price (logged in `docs/CHANGELOG.md`; the frozen version's hash is in docs/PREREG.md). Check the config matches it:

   ```bash
   shasum -a 256 config/bench.json      # equals config_sha256 in run-plan.json
   ```
3. **Re-score from scratch:** with access to our private run folders, answer keys and overlay (an independent reviewer can ask for them: open an issue titled "Data request"; requests are answered until 90 days after publication, and after that the run folders are deleted), put them in `private/` and run:

```bash
./bench audit           # every run file matches results/manifest.json; no credentials; results clean
scripts/reproduce.sh    # re-scores every run and compares the rebuilt summary.csv with the committed one
```

The script re-scores a temporary copy of `private/`, so the run files that `results/manifest.json` hashes are never rewritten.

If you get this far, or get stuck, please tell us: open a "Reproduction report" issue. Attempts are logged in [REPRODUCTIONS.md](REPRODUCTIONS.md).

## B. Re-run the benchmark

### 1. Accounts

| Service | Used for | Notes |
|---|---|---|
| Clay | The `clay_waterfall` and `clay_single` endpoints | A plan with API access. About $370 of credits for the waterfall arm and $240 for the single-provider arm on 500 contacts, at November 2026 prices |
| Two single-database providers | `provider_a_enrich`, `provider_b_match` | Ours are anonymized. Choose your own vendors and write an adapter for each (step 4) |
| ZeroBounce | Verifying every returned email | About 1,500 credits for four endpoints |
| Twilio | Checking returned phone numbers (Lookup, line type) | A Standard API key: its SID and secret |
| SEC EDGAR and UK Companies House | Building the input and answer keys | Free. The SEC needs a contact in every request; Companies House needs a free API key |

### 2. Credentials

```bash
cp .env.example .env
```

Fill in only what you run. `.env` and `private/` are gitignored; never commit them.

### 3. Clay functions

The Clay adapter runs Clay functions by ID, set in `.env`:

| Variable | What to point it at |
|---|---|
| `CLAY_ROUTINE_ID_COMPANY` | Clay's managed **Enrich Company** function |
| `CLAY_ROUTINE_ID_WATERFALL` | Clay's managed **Work Email** function (its default email waterfall) |
| `CLAY_ROUTINE_ID_LINKEDIN` | Clay's managed **Person LinkedIn URL** function |
| `CLAY_ROUTINE_ID_PHONE_WATERFALL` | Clay's managed **Mobile Phone Number** function (its default phone waterfall) |
| `CLAY_ROUTINE_ID_SINGLE` | A function you build in the Clay app: the Work Email waterfall cut to its first provider only, with that provider's own validation |
| `CLAY_ROUTINE_ID_PHONE_SINGLE` | A function you build in the Clay app: the phone waterfall cut to its first provider only |

The IDs (`function:t_...`) are specific to each workspace: find yours in the Clay app or with `clay routines list`. The docstring at the top of `providers/clay.py` describes each function's inputs and the API calls the adapter makes. Record which provider your single-provider arm uses in `config/bench.json` (`disclosures.control_provider`) before freezing.

### 4. Competitor endpoints

The committed config labels the competitors only as `provider_a` and `provider_b`. For each vendor you choose:

- Describe it in `private/platforms.json`, which is merged into the config. A made-up example:

  ```json
  {
    "platforms": {
      "provider_a": {
        "name": "Example Data Co",
        "agent_interface": "Example Data Co's enrichment API",
        "tiers": {"reference": {"plan_monthly": 99, "seat_price": 0}},
        "unit_prices": {"credits": 0.10},
        "unit_price_notes": "Plan One: $99 a month for 1,000 credits; extra credits $0.10 each (seen 2027-01-15)",
        "unit_price_sources": ["https://example.com/pricing"]
      },
      "provider_b": {
        "name": "Sample Contacts Inc",
        "agent_interface": "Sample Contacts Inc's match API",
        "tiers": {"reference": {"plan_monthly": 49, "seat_price": 0}},
        "unit_prices": {"credits": 0.20},
        "unit_price_notes": "Plan Two: $49 a month for 250 credits; extra credits $0.20 each (seen 2027-01-15)",
        "unit_price_sources": ["https://example.org/pricing"]
      }
    },
    "anonymity_extra_terms": ["example.com", "Example Enrich API", "example.org", "Plan Two"],
    "holdout": {"salt": "a-private-random-string"}
  }
  ```

  The keys under `platforms` must be `provider_a` and `provider_b`, as in `config/bench.json`, and the tier must be called `reference`. `unit_prices` holds your run-date price for each unit you record with `bench usage`. `anonymity_extra_terms` lists anything that would name a vendor (domains, product and tier names): `bench check-anon` fails if a real name or one of these terms appears in `results/`. `holdout.salt` picks the held-out rows.
- Write an adapter in `private/providers/` and register it in `private/providers/__init__.py`. Follow the shape of `providers/clay.py` and import shared helpers from `providers/common.py`: one enrichment call per contact, the same three input fields, retries only on 429, 5xx and no response (`METHODOLOGY.md` section 5).

If you name your vendors in your results, drop them from `anonymity_extra_terms`.

### 5. Input and answer keys

Build a fresh sample with [bench-data](https://github.com/heterochromatic/bench-data), which reads only public filings and registers. `docs/DATA.md` lists the input's columns and segment labels; `docs/ANSWER-KEYS.md` says how each key is built and reviewed. Run it from a `bench-data` checkout next to this repo:

```bash
git clone --branch v0.1.4 https://github.com/heterochromatic/bench-data.git ../bench-data && cd ../bench-data
OUT=../clay-waterfall-enrichment-benchmark/private/datasets/candidates
export SEC_CONTACT="Your Name you@example.com"
export COMPANIES_HOUSE_KEY=...
# 1. Candidate pools: US small (private), US mid-market and enterprise (public), EMEA small (UK)
python3 -m benchdata formd --since <date> --until <date> --out $OUT
python3 -m benchdata domains --companies $OUT/formd-filings.csv --executives $OUT/formd-executives.csv --out $OUT
python3 -m benchdata public-contacts --since <date> --until <date> --out $OUT
python3 -m benchdata uk-contacts --out $OUT
# 2. Known-email (gold) candidates, before assembling: w1-assemble reads them
python3 -m benchdata press-contacts --ciks $OUT/public-contacts.candidates.csv --since <date> --out $OUT
# 3. Assemble: writes w1-input, w1-email-gold and w1-firmographics-truth candidates, capped per size x region cell
python3 -m benchdata w1-assemble --candidates $OUT --out $OUT
# 4. Re-check every key row against its cited source
python3 -m benchdata verify-sources --file $OUT/w1-email-gold.candidates.csv --out $OUT
python3 -m benchdata verify-sources --file $OUT/w1-firmographics-truth.candidates.csv --out $OUT
```

Use dates in the past: Form D and Form 3/4 windows of a few months give enough rows. `firmographics --ciks <file> --headcount` can fill missing headcounts for public companies in the firmographic sample (`<file>` is any CSV with a `cik` column).

Every command writes **candidates** (`*.candidates.csv`). Review them as `docs/ANSWER-KEYS.md` describes, then save the reviewed rows as `w1-input.csv`, `w1-email-gold.csv` and `w1-firmographics-truth.csv` in `private/datasets/`.

### 6. Freeze, then run

A fresh clone carries our run plan. Start your own:

```bash
rm results/run-plan.json results/manifest.json results/summary.csv
./bench sanity
./bench export-public
./bench freeze
./bench run --task W1 --env "self-serve monthly" --endpoints clay_waterfall --limit 5   # smoke test, recorded as Void
./bench run --task W1 --env "self-serve monthly"                                         # every endpoint, one run each
```

`freeze` stops if a dataset is missing or `results/run-plan.json` already exists (delete it to re-freeze your own copy). `provider_a_enrich` and `provider_b_match` are only known once your private adapters are registered (step 4).

Then for each run:

```bash
./bench usage <run_id> --units data_credits=<n>    # Clay: read `clay credits balance` before and after the run (keep the workspace otherwise idle) and enter the drop; others: --before/--after balance
./bench verify <run_id> --mode zerobounce --phone-mode twilio
./bench score <run_id>
./bench summary && ./bench manifest && ./bench audit
```

`./bench run --resume <run_id>` continues an interrupted run without re-calling finished rows. `METHODOLOGY.md` has the full rules.

## Continuous integration

The vendor-name check runs locally, not in CI, so the names are never stored on GitHub: `scripts/check_names.sh` searches every commit and commit message for the terms in `private/anon-terms.txt` (gitignored, one name or identifying term per line). In a fork, list your own vendors there. Dependabot keeps GitHub Actions pins current (monthly).

## Known differences you should expect

- **Different sample, different numbers.** Your input comes from a different filing window.
- **Vendor data changes.** Coverage moves week to week, and Clay's default waterfalls change their provider lists over time.
- **EMEA coverage.** Free public sources cover small UK companies only; larger EMEA companies and APAC aren't covered (recorded as shortfalls in `METHODOLOGY.md`).
