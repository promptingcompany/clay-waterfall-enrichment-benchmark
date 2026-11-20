#!/usr/bin/env python3
"""Keep the published numbers in step with results/summary.csv.

    python scripts/check_results.py           # check; exits 1 with a diff if anything is out of date
    python scripts/check_results.py --write   # rebuild the generated tables in RESULTS.md, then check

Tables in RESULTS.md sit between `<!-- generated:NAME -->` and `<!-- /generated -->` and are rebuilt from the CSV.
Figures in RESULTS.md's sentences and in README.md's Results section are hand-written; they are checked, not rewritten.
The ranges in brackets are 95% Wilson score intervals, worked out here from each rate and its sample size.
"""
import csv
import difflib
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
with open(REPO / "results" / "summary.csv", newline="", encoding="utf-8") as f:
    ROWS = {r["endpoint"]: r for r in csv.DictReader(f)}
CW, CS, PA, PB = "clay_waterfall", "clay_single", "provider_a_enrich", "provider_b_match"


def val(endpoint, column):
    return float(ROWS[endpoint][column + "_median"])


def pct(x):
    return f"{round(x * 100)}%"


def usd(x):
    return f"${int(x + 0.5):,}"  # half rounds up: 838.5 is $839


def seconds(ms):
    return f"{ms / 1000:.0f} s" if ms >= 10_000 else f"{ms / 1000:.1f} s"


COLUMNS = [  # table header, summary.csv column (without _median), format
    ("Verified email rate", "verified_email_rate", pct),
    ("Right-person rate (gold subset)", "gold_email_precision", pct),
    ("Email fill", "email_fill_rate", pct),
    ("Valid mobile rate", "valid_phone_rate", pct),
    ("Firmographic accuracy", "firmographic_accuracy", pct),
    ("$ / 1k verified", "cost_per_1000_accepted_usd", usd),
    ("Median latency", "median_latency_ms", seconds),
]


CONTACTS = 500   # input rows: the sample behind every email and phone rate (docs/DATA.md)
GOLD_ROWS = 128  # contacts in the gold subset (docs/CHANGELOG.md, 2026-11-06)
CI_COLUMNS = ("verified_email_rate", "gold_email_precision", "valid_phone_rate")


def sample(endpoint, column):
    """How many contacts a rate is measured on."""
    if column != "gold_email_precision":
        return CONTACTS
    # Right-person rate = exact matches ÷ gold contacts an email came back for; recall = exact matches ÷ all gold contacts.
    return round(round(val(endpoint, "gold_email_recall") * GOLD_ROWS) / val(endpoint, column))


def interval(endpoint, column, z=1.96):
    """95% Wilson score interval, from the rate as summary.csv rounds it (so a bound can be a point off the exact count's)."""
    p, n = val(endpoint, column), sample(endpoint, column)
    centre, half = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / (1 + z * z / n), (centre + half) / (1 + z * z / n)


def span(endpoint, column):
    low, high = interval(endpoint, column)
    return f"{round(low * 100)}–{round(high * 100)}%"


def table(endpoints):
    lines = ["| Vendor | Endpoint | " + " | ".join(c[0] for c in COLUMNS) + " |", "|" + "---|" * (len(COLUMNS) + 2)]
    for e in sorted(endpoints, key=lambda e: val(e, "cost_per_1000_accepted_usd")):  # pre-registered ranking (METHODOLOGY)
        cells = " | ".join(fmt(val(e, col)) + (f" ({span(e, col)})" if col in CI_COLUMNS else "") for _, col, fmt in COLUMNS)
        lines.append(f"| {ROWS[e]['platform_label']} | `{e}` | {cells} |")
    return "\n".join(lines)


BLOCKS = {"waterfall-table": table([CW]), "single-provider-table": table([e for e in ROWS if e != CW])}


def rates(column, *endpoints):
    return [pct(val(e, column)) for e in endpoints]


def count(column):
    return str(round(val(CW, column)))


# Each list is the figures of one sentence in RESULTS.md: they must appear in this order on one line.
SENTENCES = [
    rates("verified_email_rate", CW, PB, PA),
    rates("verified_email_rate", CS, PB, PA),
    rates("valid_phone_rate", CW, PB, PA, CS),
    rates("valid_phone_rate", CW, CS) + rates("verified_email_rate", CW, CS),
    [r for e in (CW, CS, PB, PA) for r in rates("verified_email_rate_na", e) + rates("verified_email_rate_emea", e)],
    [count("n_vertical_software")] + rates("verified_email_rate_vertical_software", CW, CS, PB, PA)
    + [count("n_startup_y")] + rates("verified_email_rate_startup_y", CW, CS, PB, PA),
    rates("firmographic_accuracy", CW, PB, PA) + rates("band_accuracy", PB) + rates("industry_accuracy", CW),
    [span(e, "verified_email_rate") for e in (CW, CS, PB, PA)] + [span(e, "valid_phone_rate") for e in (CW, PB, CS, PA)]
    + [f"{min(sample(e, 'gold_email_precision') for e in ROWS)}–{max(sample(e, 'gold_email_precision') for e in ROWS)}"],
]

# RESULTS.md's confidence-interval paragraph says these pairs, and no others, have intervals that don't overlap (higher first).
APART = {"verified_email_rate": {(CW, PB), (CW, PA), (CS, PB), (CS, PA), (PB, PA)},
         "valid_phone_rate": {(CW, PB), (CW, CS), (CW, PA), (PB, CS), (PB, PA)},
         "gold_email_precision": set()}


def published():
    """Every rate and cost per 1,000 in summary.csv, as it would be printed."""
    out = set()
    for row in ROWS.values():
        for column, v in row.items():
            if column.endswith("_median") and v:
                if re.search("rate|accuracy|precision|recall", column):
                    out.add(pct(float(v)))
                elif column.startswith("cost_per_1000"):
                    out.add(usd(float(v)))
    return out


def in_order(figures, text):
    """Does one line of `text` have these figures in this order?"""
    return re.search(".*".join(r"\b" + re.escape(x) for x in figures), text)


def regenerate(text):
    return re.sub(r"(<!-- generated:([\w-]+) -->\n).*?(<!-- /generated -->)",
                  lambda m: m.group(1) + BLOCKS[m.group(2)] + "\n" + m.group(3), text, flags=re.S)


def problems(results, readme):
    out = [f"RESULTS.md: no <!-- generated:{name} --> block" for name in BLOCKS if f"generated:{name} -->" not in results]
    out += difflib.unified_diff(results.splitlines(), regenerate(results).splitlines(),
                                "RESULTS.md", "RESULTS.md rebuilt from results/summary.csv", lineterm="")
    for figures in SENTENCES:
        if not in_order(figures, results):
            out.append("RESULTS.md: no line has these figures from summary.csv in this order: " + ", ".join(figures))
    for column, claimed in APART.items():
        apart = {(a, b) for a in ROWS for b in ROWS if interval(a, column)[0] > interval(b, column)[1]}
        if apart != claimed:
            out.append(f"RESULTS.md's confidence-interval paragraph is out of date for {column}: the intervals that don't "
                       f"overlap are now {sorted(apart)}")
    # README Results: its headline gives Clay's waterfall's verified email rate, then its valid mobile rate; every figure
    # it quotes is in summary.csv; and Clay's waterfall has the highest rates it claims.
    section = re.search(r"^## Results\n(.*?)(?=^## |\Z)", readme, re.S | re.M)
    section = section.group(1) if section else ""
    headline = rates("verified_email_rate", CW) + rates("valid_phone_rate", CW)
    if not section:
        out.append("README.md: no ## Results section")
    elif not in_order(headline, section):
        out.append("README.md Results: no line has these figures from summary.csv in this order: " + ", ".join(headline))
    quoted = set(re.findall(r"\$[\d,.]*\d|\d[\d.]*%", section))
    if quoted - published():
        out.append(f"README.md Results quotes {sorted(quoted - published())}, which summary.csv doesn't give")
    for column in ("verified_email_rate", "valid_phone_rate"):
        if max(ROWS, key=lambda e: val(e, column)) != CW:
            out.append(f"README.md Results says {CW} has the highest {column}; summary.csv disagrees")
    return out


def main():
    path = REPO / "RESULTS.md"
    results = path.read_text(encoding="utf-8")
    if "--write" in sys.argv[1:]:
        results = regenerate(results)
        path.write_text(results, encoding="utf-8")
    found = problems(results, (REPO / "README.md").read_text(encoding="utf-8"))
    print("\n".join(found) if found else "published numbers match results/summary.csv")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
