# Benchmark card: Enrichment Waterfall Benchmark

**Purpose.** To test one claim: that a multi-provider enrichment waterfall finds more verified work emails and working mobiles than a single-provider database, and at what cost.

The method and results have not been independently reviewed.

**Results as of 7 November 2026.** These results reflect each vendor's data and APIs on 7 November 2026 (UTC), the day all four runs were made ([RESULTS.md](../RESULTS.md#versions-and-dates)). Vendor data changes often: re-run before relying on them after mid-2027, or after a vendor changes its product.

## What it measures

Four API endpoints were each given the same 500 contacts (first name, last name, company domain): Clay's default waterfall, Clay limited to one provider per field, and two anonymized single-database providers. For each endpoint it reports:

- verified email rate, email fill rate and right-person rate;
- valid mobile rate;
- firmographic accuracy (employee band, industry, HQ country);
- cost per 1,000 verified emails and median latency;
- verified email rate by region, company size, industry and other cuts.

Definitions are in [METHODOLOGY.md](../METHODOLOGY.md), and the numbers are in [RESULTS.md](../RESULTS.md).

## What it doesn't measure

- Ease of use, the app's interface, CRM write-back or intent data.
- How fresh the data stays over time, or how results vary from day to day.
- APAC, or mid-market and enterprise companies in EMEA: free first-hand sources didn't cover enough of them.
- Any vendor other than the four endpoints tested, or any plan other than the ones priced.

## Intended uses

- Deciding whether a waterfall is worth its cost over a single provider for list enrichment.
- Re-running the same method on your own sample and vendors ([REPRODUCE.md](REPRODUCE.md)).
- Checking our scoring against the published summary and manifest.

## Out-of-scope uses

- Ranking the two anonymized providers by name. They are not named, and the benchmark isn't a verdict on any named vendor other than Clay.
- Choosing a tool for real-time, per-contact lookups from these latency figures alone: Clay's runs were batched.
- Quoting one rate without its interval, its sample or its date. Vendor data changes week to week.

## Data

500 business contacts listed publicly on company websites and in public filings and registers (SEC and UK Companies House), in four size and region cells. 128 of them have a known email (the gold subset) and 196 have a checked firmographic answer key. The input holds people's names, so it is never published; its checksum is in `results/run-plan.json`. Details are in [DATA.md](DATA.md) and [ANSWER-KEYS.md](ANSWER-KEYS.md); how the contacts' details were handled is in [PRIVACY.md](PRIVACY.md).

## Known limitations

- **One run per endpoint.** Run-to-run variation wasn't measured. The intervals in RESULTS.md cover chance in the sample only.
- **Anonymized vendors.** Provider A and Provider B aren't named, and their adapters and prices aren't published, so their arms can't be re-run exactly.
- **Provider A's price.** It was priced at its self-serve top-up rate, not a negotiated or plan-included rate, and it was tested through its self-serve command-line product.
- **Held-out rows.** 30% of rows are held out and never published. Their verified email rates are reported by hand from the run records, not from `results/summary.csv`.
- **Clay's batch latency.** Clay's enrichments run as asynchronous batches polled every 30 seconds, so its latency isn't directly comparable with the others' synchronous calls.
- **Sample bias.** Filings lean towards executives and public or regulated companies, who may be easier to find than average.
- **Not independently reviewed.** Competitors were not offered a review before publication.

## Maintenance and contact

Maintained by The Prompting Company. Report an error with the "Results or scoring error" issue template, and a reproduction attempt with "Reproduction report" ([CONTRIBUTING.md](CONTRIBUTING.md)). Report security or personal-data concerns privately ([SECURITY.md](../SECURITY.md)). Corrections are logged in [CHANGELOG.md](CHANGELOG.md). The private run folders are kept, and data requests answered, until 90 days after publication.
