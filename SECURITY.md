# Security policy

## Reporting a vulnerability

Please report security problems privately through GitHub: open this repository's **Security** tab and choose **Report a vulnerability**. Don't open a public issue for a security problem.

Include what you found, where (file and line, or the command you ran), and how to reproduce it. We aim to acknowledge reports within 5 business days.

## What counts

- Code that could leak a credential: an API key, token or `.env` value reaching a log, an audit file, a transcript or a committed file.
- Personal data reaching a committed file: a person's name, email address or phone number. This repo publishes company-level data and aggregates only; contact-level data stays in the gitignored `private/` folder.
- Anything that lets a benchmark run reach a live system it shouldn't: a real CRM instead of the test portal, or a real outreach channel.
- A vulnerability in a dependency or in the GitHub Actions this repo uses.

## Data concerns

If you believe your own details were used to build a benchmark input, report it the same way. Inputs come only from public filings and registers and are never published. They are deleted, with the run folders, 90 days after the results are published.

## Supported versions

Only the latest commit on `main` and the most recent release tag are supported.

## Handling secrets in this repo

- Credentials live only in a local `.env` file, which is gitignored. `.env.example` lists the names, never values.
- `bench audit` fails if any credential survives redaction in a run file.
- CI runs gitleaks on every push; GitHub secret scanning and push protection are turned on when the repository is public.
