# Privacy

This benchmark used real people's business contact details. The Prompting Company ran it and decided how the data was used (the "controller", in GDPR terms).

## What data, and where it came from

- **Input: 500 business contacts.** First name, last name and company domain, plus labels used only for scoring (company size, region, industry, seniority and job function). They are business contacts listed publicly on company websites and in public filings and registers: US SEC filings and the UK Companies House register ([DATA.md](DATA.md); sources in [ANSWER-KEYS.md](ANSWER-KEYS.md#sources)). They were sampled from a pool of 1,127 contacts collected the same way; 5 other rows from that pool were used in a smoke test ([CHANGELOG.md](CHANGELOG.md)).
- **Known emails.** For 128 of the 500, a work email printed on their company's own site or in a filing.
- **Output.** The work emails, phone numbers and company details the vendors returned, their raw responses (which can hold other details, such as a LinkedIn profile URL), and whether each email and phone passed its check.

## Why, and on what basis

- **Purpose:** scoring this benchmark, and letting a reviewer check the scores. Nothing else.
- **No outreach.** Nobody in the data was emailed, called or messaged, and the data isn't used for sales or marketing.
- **Lawful basis:** legitimate interests (Article 6(1)(f) of the GDPR and the UK GDPR): research into how well enrichment tools work. We believe this is fair to the people involved: the data was already public, it is about their professional roles only, nobody was contacted, nothing personal is published and it is kept for a short, fixed time.
- **GDPR and UK GDPR.** 115 of the 500 are directors of UK companies, and other people in the sample may live in the UK or the EU, so we treat both laws as applying.

## Who received it

Each contact's name and company domain went to the endpoints tested: Clay, whose waterfalls look contacts up with other data providers (the email providers are listed in [RESULTS.md](../RESULTS.md#waterfall-against-a-single-provider)), Provider A and Provider B. Returned emails went to ZeroBounce, and returned phone numbers to Twilio Lookup, to be checked.

## What is published

No personal data. This repository holds only totals and rates (`results/summary.csv`), checksums and file hashes (`results/run-plan.json`, `results/manifest.json`) and company-level answer-key rows with no person in them (`datasets/public/`). CI fails if the `private/` folder is committed or if an email address appears in `results/`.

## Who can see the private files

The input, answer keys, run folders and raw vendor responses are held by The Prompting Company in a `private/` folder that git ignores. An independent reviewer can ask for access, to check them against the published manifest, by opening an issue titled "Data request" ([DATA.md](DATA.md)). They are shared with reviewers only, and only for that.

## How long it's kept

Data requests are answered until 90 days after publication. After that the inputs and the run folders are deleted ([DATA.md](DATA.md), [SECURITY.md](../SECURITY.md)).

Three files are kept after that, so the answer keys can be re-checked and later reproductions scored against the same evidence: the gold-email answer key (known work emails and their public sources), the verifier cache (each checked email or number with its verdict) and the pool of 1,127 candidate contacts the 500 were drawn from. They stay in the same private folder with the same access rules, and anyone in them can still ask to be removed as described below.

## Ask what we hold, or ask to be removed

If you think you are in this data, you can ask what we hold about you, ask us to delete it, or object to our using it. Email [support@promptingco.com](mailto:support@promptingco.com) with the subject "Privacy request", or report it privately through GitHub: open this repository's **Security** tab, choose **Report a vulnerability** and title it "Privacy request" ([SECURITY.md](../SECURITY.md)). Please don't put personal details in a public issue. We aim to acknowledge reports within 5 business days.

Deleting your details doesn't change the published totals, which identify no one. You can also complain to your data protection authority (in the UK, the Information Commissioner's Office).
