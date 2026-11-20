# Data dictionary

What every column means in the CSV files this repository publishes. The scorer is `score_w1` in [`scoring/scorers.py`](../scoring/scorers.py). The functions named `scoring.…`, `summary.…`, `costs.…`, `runs.…` and `adapters.…` are in [benchkit](https://github.com/heterochromatic/benchkit), pinned in `requirements.txt`. Metric rules in full: [METHODOLOGY.md](../METHODOLOGY.md) section 6. Denominators: [DATA.md](DATA.md#denominators).

## `results/summary.csv`

One row per endpoint, four rows. Written by `bench summary` (`summary.write_all`) from the four run records.

How to read it:

- **`_median`, `_min`, `_max`:** the median, lowest and highest value across an endpoint's ranked runs, rounded to 2 decimal places (`summary._stats`). Each endpoint ran once, so all three are that one run's value.
- **Rates** are fractions from 0 to 1, so 0.59 is 59%. Unless a row says otherwise they divide by all 500 input rows, and a failed call or an empty result counts as a miss.
- **Blank** means not measured, or not applicable to this benchmark.

### Identity and run counts

| Column | Meaning | Unit | How it's computed |
|---|---|---|---|
| `task_id` | The task | text (`W1`) | From the run record |
| `task_version` | Version of the task spec ([tasks/W1-v1.md](../tasks/W1-v1.md)) | text (`W1-v1`) | From the run record |
| `platform_label` | The vendor, as published. Two are anonymized as Provider A and Provider B | text | The platform's `label` in `config/bench.json` |
| `endpoint` | Which endpoint ran ([README roster](../README.md#task)) | text | The adapter's endpoint ID |
| `executor` | Who ran the task. `script` means an API adapter, with no AI agent and no person | text | From the run record |
| `operator_profile` | Kind of operator. `script` for every run here | text | From the run record |
| `cost_runs` | Runs whose cost counts: the first ranked run on each vendor account (METHODOLOGY.md section 5, rule 8) | count | `summary.cost_counted` |
| `runs` | Runs recorded for the endpoint | count | `summary.write_all` |
| `ranked_runs` | Runs with a status that is ranked: Pass, Partial, Fail or Did not finish | count | `summary.write_all` |
| `statuses` | How many runs ended with each status (METHODOLOGY.md section 8), such as `Pass=1` | text | `score_w1`: Pass at or above the quality floor (a 40% verified email rate), Partial below it, Fail if an input row is missing from the output |
| `environment_labels` | The kind of account the runs used | text | From the run record |

### Time, cost and latency

| Column | Meaning | Unit | How it's computed |
|---|---|---|---|
| `steps_median`, `steps_min`, `steps_max` | Steps a person took. Blank: no person ran these tasks | count | Recorded for human runs only |
| `active_min_median`, `active_min_min`, `active_min_max` | Hands-on time. Blank for the same reason | minutes | Recorded for human runs only |
| `wallclock_min_median`, `wallclock_min_min`, `wallclock_min_max` | Time from the start of the run to its end, including any pause before a resume | minutes | `runs.stop`: stop time minus start time |
| `accepted_rate_median`, `accepted_rate_min`, `accepted_rate_max` | Share of the 500 contacts with an accepted record. For this task that is the verified email rate | fraction of 500 | `score_w1`: accepted records ÷ input rows |
| `cost_per_accepted_record_usd_median`, `cost_per_accepted_record_usd_min`, `cost_per_accepted_record_usd_max` | Usage cost per verified email | US dollars | `costs.run_costs`: units the run used × the reference tier's unit price, ÷ verified emails |
| `cost_per_1000_accepted_usd_median`, `cost_per_1000_accepted_usd_min`, `cost_per_1000_accepted_usd_max` | $ / 1k verified, the ranking metric | US dollars | `summary.run_row`: cost per accepted record × 1,000 |
| `agent_cost_usd_median`, `agent_cost_usd_min`, `agent_cost_usd_max` | Cost of an AI agent. Blank: none was used | US dollars | Recorded for agent runs only |
| `median_latency_ms_median`, `median_latency_ms_min`, `median_latency_ms_max` | Median time per contact to the email result, over successful requests only. For Clay it is wall time through its routines, to within one 30-second poll | milliseconds | `adapters`: median of each contact's `latency_ms` |

### Email, phone and company-data metrics

| Column | Meaning | Unit | How it's computed |
|---|---|---|---|
| `email_fill_rate_median` | Rows with any email returned | fraction of 500 | `score_w1` |
| `verified_email_rate_median` | The headline. Rows whose email the verifier (ZeroBounce) marks `valid` and that is on the company's domain or a recorded alias | fraction of 500 | `score_w1`, with `scoring.accepted_email` |
| `off_domain_valid_emails_median` | Emails the verifier marks valid that are not on the company's domain, so they don't count as verified | count of rows | `score_w1` |
| `gold_email_precision_median` | Right-person rate. On the gold subset, returned emails that are exactly the known address | fraction of the gold contacts an email came back for | `scoring.gold_metrics` |
| `gold_email_recall_median` | Gold contacts whose exact known address was returned | fraction of the 128 gold contacts | `scoring.gold_metrics` |
| `gold_phone_precision_median`, `gold_phone_recall_median` | The same for phones. Blank: the gold subset has no known phone numbers | fraction | `scoring.gold_metrics` |
| `phone_fill_rate_median` | Rows with any phone returned | fraction of 500 | `score_w1` |
| `valid_phone_rate_median` | Rows whose phone the phone checker (Twilio Lookup, line type) confirms as a valid mobile | fraction of 500 | `score_w1`, with `scoring.phone_ok` |
| `firmographic_accuracy_median` | Answer-key rows where employee band, industry and HQ country all match | fraction of the 170 key rows that have all three | `score_w1` |
| `band_accuracy_median` | The employee count is in the same band as the key's. Bands: 1–10, 11–50, 51–200, 201–500, 501–1,000, 1,001–5,000 and over 5,000 (`employee_bands` in `config/bench.json`) | fraction of the 196 key rows | `score_w1`, with `band` |
| `industry_accuracy_median` | The vendor's industry label, mapped with `datasets/industry-map.csv`, is the key's industry | fraction of the 170 key rows with an industry | `score_w1`, with `industry_map` |
| `country_accuracy_median` | The HQ country code is the key's | fraction of the 196 key rows | `score_w1` |

### Segment cuts

Each rate column is the verified email rate among the input rows with that label, as a fraction from 0 to 1 (`score_w1`). Each `n_` column is how many of the 500 input rows have the label, so it is the same for every endpoint. Labels come from the input file and are never sent to a vendor ([DATA.md](DATA.md)). A cut with fewer than 30 rows is indicative only.

Size and region cuts have no `n_` column. From `disclosures.cells.counts` in `config/bench.json`: 229 small, 110 mid-market and 160 enterprise rows (one row has no size); 385 North America and 115 EMEA.

| Cut | Rate column | Row-count column |
|---|---|---|
| Small companies (1–50 employees) | `verified_email_rate_smb_median` | none |
| Mid-market (51–1,000) | `verified_email_rate_mid_median` | none |
| Enterprise (1,001+) | `verified_email_rate_ent_median` | none |
| North America (US, Canada, Mexico) | `verified_email_rate_na_median` | none |
| EMEA | `verified_email_rate_emea_median` | none |
| APAC (blank: no APAC rows) | `verified_email_rate_apac_median` | none |
| Industry: `education` | `verified_email_rate_vertical_education_median` | `n_vertical_education_median` |
| Industry: `energy_and_utilities` | `verified_email_rate_vertical_energy_and_utilities_median` | `n_vertical_energy_and_utilities_median` |
| Industry: `financial_services` | `verified_email_rate_vertical_financial_services_median` | `n_vertical_financial_services_median` |
| Industry: `healthcare` | `verified_email_rate_vertical_healthcare_median` | `n_vertical_healthcare_median` |
| Industry: `hospitality_and_travel` | `verified_email_rate_vertical_hospitality_and_travel_median` | `n_vertical_hospitality_and_travel_median` |
| Industry: `it_services` | `verified_email_rate_vertical_it_services_median` | `n_vertical_it_services_median` |
| Industry: `manufacturing` | `verified_email_rate_vertical_manufacturing_median` | `n_vertical_manufacturing_median` |
| Industry: `marketing_and_media` | `verified_email_rate_vertical_marketing_and_media_median` | `n_vertical_marketing_and_media_median` |
| Industry: `professional_services` | `verified_email_rate_vertical_professional_services_median` | `n_vertical_professional_services_median` |
| Industry: `real_estate_and_construction` | `verified_email_rate_vertical_real_estate_and_construction_median` | `n_vertical_real_estate_and_construction_median` |
| Industry: `retail_and_ecommerce` | `verified_email_rate_vertical_retail_and_ecommerce_median` | `n_vertical_retail_and_ecommerce_median` |
| Industry: `software` | `verified_email_rate_vertical_software_median` | `n_vertical_software_median` |
| Industry: `telecommunications` | `verified_email_rate_vertical_telecommunications_median` | `n_vertical_telecommunications_median` |
| Industry: `transportation_and_logistics` | `verified_email_rate_vertical_transportation_and_logistics_median` | `n_vertical_transportation_and_logistics_median` |
| Startup (privately funded, from SEC Form D): `n` | `verified_email_rate_startup_n_median` | `n_startup_n_median` |
| Startup: `y` | `verified_email_rate_startup_y_median` | `n_startup_y_median` |
| Agency (advertising, media-buying or PR): `n` | `verified_email_rate_agency_n_median` | `n_agency_n_median` |
| Agency: `y` | `verified_email_rate_agency_y_median` | `n_agency_y_median` |
| Seniority: `c_suite` | `verified_email_rate_seniority_c_suite_median` | `n_seniority_c_suite_median` |
| Seniority: `director` | `verified_email_rate_seniority_director_median` | `n_seniority_director_median` |
| Seniority: `executive` | `verified_email_rate_seniority_executive_median` | `n_seniority_executive_median` |
| Seniority: `other` | `verified_email_rate_seniority_other_median` | `n_seniority_other_median` |
| Seniority: `vp` | `verified_email_rate_seniority_vp_median` | `n_seniority_vp_median` |
| Job function: `engineering_it` | `verified_email_rate_function_engineering_it_median` | `n_function_engineering_it_median` |
| Job function: `executive` | `verified_email_rate_function_executive_median` | `n_function_executive_median` |
| Job function: `finance` | `verified_email_rate_function_finance_median` | `n_function_finance_median` |
| Job function: `hr` | `verified_email_rate_function_hr_median` | `n_function_hr_median` |
| Job function: `legal` | `verified_email_rate_function_legal_median` | `n_function_legal_median` |
| Job function: `marketing` | `verified_email_rate_function_marketing_median` | `n_function_marketing_median` |
| Job function: `operations` | `verified_email_rate_function_operations_median` | `n_function_operations_median` |
| Job function: `other` | `verified_email_rate_function_other_median` | `n_function_other_median` |
| Job function: `sales` | `verified_email_rate_function_sales_median` | `n_function_sales_median` |
| Ownership: `private` | `verified_email_rate_ownership_private_median` | `n_ownership_private_median` |
| Ownership: `public` | `verified_email_rate_ownership_public_median` | `n_ownership_public_median` |
| Funding raised (startups only): `10m_plus` | `verified_email_rate_funding_10m_plus_median` | `n_funding_10m_plus_median` |
| Funding raised: `1m_10m` | `verified_email_rate_funding_1m_10m_median` | `n_funding_1m_10m_median` |
| Funding raised: `under_1m` | `verified_email_rate_funding_under_1m_median` | `n_funding_under_1m_median` |

### Projected cost and price date

| Column | Meaning | Unit | How it's computed |
|---|---|---|---|
| `fully_loaded_monthly_usd` | Projected cost of enriching 5,000 records a month with 3 users (`scenario` in `config/bench.json`). Blank for Provider A, which has no monthly plan or seat price recorded | US dollars per month | `costs.fully_loaded`: the reference tier's monthly plan price, plus seats, plus usage at the run's units per input row |
| `fully_loaded_per_record_usd` | That monthly cost per record | US dollars | `costs.fully_loaded`: monthly cost ÷ 5,000 |
| `price_effective_date` | The date the unit prices were confirmed | date (YYYY-MM-DD) | `price_effective_date` in `config/bench.json` |

## `datasets/public/w1-firmographics-public.csv`

The company-level answer-key rows outside the held-out set: 128 rows, one per company, with no person in them. Written by `bench export-public` (`export_firmographics` in `scoring/scorers.py`). The first line is the canary comment; the header is the second line. How the key was built: [ANSWER-KEYS.md](ANSWER-KEYS.md).

| Column | Meaning | Unit | How it's computed |
|---|---|---|---|
| `company_domain` | The company's website domain | text | From the input row. The first key row for each domain is kept |
| `true_employee_count` | The company's employee count | whole number of people | From its SEC 10-K or its UK Companies House accounts |
| `true_industry` | One of the 15 shared industries, or `unknown`. Unknown rows are left out of industry accuracy | text | The SEC or UK industry code, mapped with `datasets/industry-map.csv` |
| `true_hq_country` | HQ country | ISO 3166 alpha-2 code | The SEC business address or the register address |

## `datasets/public/w1-firmographics-sources.csv`

The SEC filing behind each public answer-key row that came from a 10-K, with a permanent Wayback Machine copy so the evidence stays checkable if the SEC page moves: 89 rows. The other 39 public rows come from UK Companies House accounts, whose document links need an API key and can't be archived; their source is the company's filed accounts on the Companies House register.

| Column | Meaning | Unit | How it's computed |
|---|---|---|---|
| `company_domain` | Joins to `w1-firmographics-public.csv` | text | From the input row |
| `source_url` | The SEC filing the employee count, industry and HQ were read from | URL | From the answer-key build (bench-data) |
| `wayback_url` | An archived copy of that filing | URL | Saved with the Wayback Machine, November 2026 |

## `datasets/industry-map.csv`

The mapping from industry labels to 15 shared industries: 177 rows. Both the answer key and every vendor's output go through it, so they use one list (`industry_map` in `scoring/scorers.py`).

| Column | Meaning | Unit | How it's computed |
|---|---|---|---|
| `vendor_label` | An industry label as a vendor or a register writes it. Matched after lower-casing and dropping punctuation (`scoring.norm`) | text | Collected from the answer-key sources and the vendors' outputs; additions after the freeze are logged in docs/CHANGELOG.md |
| `canonical_industry` | The shared industry the label maps to | text, one of 15 | Assigned with keyword rules (docs/CHANGELOG.md, 2026-11-07) |
