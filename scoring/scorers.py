"""Acceptance test for W1 (tasks/W1-v1.md), loaded by benchkit.

Accepted record = an input row whose email passes the shared verifier AND is on the company's
domain (or a recorded alias). Fill and verified rates are reported overall and per size and
region segment, so the waterfall's effect outside the US and in SMB is visible. On the gold
subset (emails listed on the company's own site) returned emails must match exactly.
Industries are compared after mapping every vendor's label to one list (datasets/industry-map.csv).
"""
import csv
import re
import sys

from benchkit import paths
from benchkit.runs import run_dir
from benchkit.sanity import mark_valid, write_rows
from benchkit.scoring import (accepted_email, check_columns, domain_aliases, email_ok, gold_metrics, holdout_ids,
                              known, load_gold, norm, output_csv, phone_ok, rate, read_csv, verifier)


def industry_map():
    _, rows = read_csv(paths.repo() / "datasets" / "industry-map.csv")
    m = {norm(r["vendor_label"]): r["canonical_industry"] for r in rows}
    m.update({norm(c): c for c in set(m.values())})
    return m


def band(n, edges):
    """Index of the employee band n falls in; None if n isn't a finite number."""
    try:
        n = int(float(str(n).replace(",", "")))
    except (ValueError, OverflowError):
        return None
    return sum(n > e for e in edges)


def score_w1(run, cfg):
    t = cfg["tasks"]["W1"]
    header, rows = output_csv(run)
    check_columns(header, t["output_columns"])
    _, inputs = read_csv(run_dir(run["run_id"]) / "input" / t["input"])
    seg = {r["input_id"]: (r["segment_size"], r["segment_region"]) for r in inputs}
    domain = {r["input_id"]: r["company_domain"] for r in inputs}
    out = {}
    for r in rows:
        if r["input_id"] in seg:
            out.setdefault(r["input_id"], r)  # first row wins: a repeated row never counts twice
    format_ok = set(seg) <= set(out)
    ver, aliases = verifier(run), domain_aliases()
    n = len(seg)

    filled = {i for i, r in out.items() if (r["email"] or "").strip()}
    valid_any = {i for i, r in out.items() if email_ok(r["email"], ver, cfg)}
    verified = {i for i in valid_any if accepted_email(out[i]["email"], domain[i], ver, cfg, aliases)}
    phones = {i for i, r in out.items() if (r["phone"] or "").strip()}
    valid_phones = {i for i, r in out.items() if phone_ok(r["phone"], ver, cfg)}

    metrics = {"format_ok": format_ok, "missing_ids": len(set(seg) - set(out)),
               "email_fill_rate": rate(len(filled), n), "verified_email_rate": rate(len(verified), n),
               "off_domain_valid_emails": len(valid_any - verified),
               "phone_fill_rate": rate(len(phones), n), "valid_phone_rate": rate(len(valid_phones), n),
               **gold_metrics(out, load_gold("w1-email-gold.csv"))}
    held = holdout_ids(seg, cfg)
    metrics["verified_email_rate_holdout"] = rate(len(verified & held), len(held))
    for dim, k in (("size", 0), ("region", 1)):
        for v in cfg["segments"][dim]:
            ids = [i for i, s in seg.items() if s[k] == v]
            metrics[f"verified_email_rate_{v}"] = rate(sum(i in verified for i in ids), len(ids))
    # Every other segment column (vertical, startup, agency, seniority, function, ownership, funding) is a
    # cut: one rate per value, plus its row count so small cuts can be shown as indicative.
    by = {r["input_id"]: r for r in inputs}
    dims = [c[len("segment_"):] for c in (inputs[0] if inputs else {}) if c.startswith("segment_") and c not in ("segment_size", "segment_region")]
    for dim in dims:
        for v in sorted({(by[i].get(f"segment_{dim}") or "") for i in seg} - {"", "unknown", "n/a"}):
            ids = [i for i in seg if by[i].get(f"segment_{dim}") == v]
            slug = re.sub(r"[^a-z0-9]+", "_", v.lower()).strip("_")
            metrics[f"verified_email_rate_{dim}_{slug}"] = rate(sum(i in verified for i in ids), len(ids))
            metrics[f"n_{dim}_{slug}"] = len(ids)

    _, truth = read_csv(paths.datasets() / "w1-firmographics-truth.csv")
    edges, imap = cfg["employee_bands"], industry_map()
    # Each field is scored only where the key knows it; "all" only where it knows all three.
    hits = {"band": 0, "industry": 0, "country": 0, "all": 0}
    checked = {"band": 0, "industry": 0, "country": 0, "all": 0}
    unmapped = {}
    for g in truth:
        o = out.get(g["input_id"]) or {}
        ind = imap.get(norm(o.get("industry")))
        if (o.get("industry") or "").strip() and ind is None:
            unmapped[o["industry"].strip()] = unmapped.get(o["industry"].strip(), 0) + 1
        true_band = band(g["true_employee_count"], edges)
        ok = {"band": None if true_band is None else band(o.get("employee_count"), edges) == true_band,
              "industry": ind == g["true_industry"].strip() if known(g["true_industry"]) else None,
              "country": ((o.get("hq_country") or "").strip().upper() == g["true_hq_country"].strip().upper()
                          if known(g["true_hq_country"]) else None)}
        ok["all"] = None if None in ok.values() else all(ok.values())
        for k, v in ok.items():
            if v is not None:
                checked[k] += 1
                hits[k] += v
    metrics["firmographic_sample"] = checked["all"]
    metrics["firmographic_accuracy"] = rate(hits["all"], checked["all"])
    for k in ("band", "industry", "country"):
        metrics[f"{k}_accuracy"] = rate(hits[k], checked[k])
    metrics["industry_unmapped_labels"] = len(unmapped)
    if unmapped:
        print(f"{len(unmapped)} vendor industry labels aren't in datasets/industry-map.csv: add them to the map "
              "(and log it in docs/CHANGELOG.md) before the scores are final; see review/industry-unmapped.csv", file=sys.stderr)
        with open(run_dir(run["run_id"]) / "review" / "industry-unmapped.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["vendor_label", "rows"])
            w.writerows(sorted(unmapped.items(), key=lambda kv: -kv[1]))

    vrate = metrics["verified_email_rate"]
    floor = vrate is not None and vrate >= t["floor"]["verified_email_rate"]
    return {"records_in": n, "accepted_records": len(verified), "accepted_rate": vrate, "metrics": metrics,
            "floor_met": floor, "proposed_status": "Fail" if not format_ok else ("Pass" if floor else "Partial")}


SCORERS = {"W1": score_w1}


def output_contacts(run, cfg):
    _, rows = output_csv(run)
    return [r["email"] for r in rows], [r["phone"] for r in rows]


def oracle_w1(run, cfg):
    """`bench sanity`: the gold emails and firmographic key written as output must score perfectly."""
    gold = {g["input_id"]: g for g in load_gold("w1-email-gold.csv")}
    tp = paths.datasets() / "w1-firmographics-truth.csv"
    truth = {g["input_id"]: g for g in read_csv(tp)[1]} if tp.exists() else {}
    if not gold and not truth:
        return {}
    rows = []
    for r in read_csv(run_dir(run["run_id"]) / "input" / cfg["tasks"]["W1"]["input"])[1]:
        g, t = gold.get(r["input_id"], {}), truth.get(r["input_id"], {})
        rows.append([r["input_id"], g.get("known_email", ""), g.get("known_phone", ""), "",
                     t.get("true_employee_count", ""), t.get("true_industry", ""), t.get("true_hq_country", "")])
    write_rows(run_dir(run["run_id"]) / "output" / "output.csv", cfg["tasks"]["W1"]["output_columns"], rows)
    mark_valid(run, [row[1] for row in rows])
    expected = {}
    if gold:
        expected |= {"gold_email_precision": 1.0, "gold_email_recall": 1.0}
    if truth:
        expected |= {"band_accuracy": 1.0, "industry_accuracy": 1.0, "country_accuracy": 1.0}
    return expected


ORACLES = {"W1": oracle_w1}


def export_firmographics(cfg):
    """Company-level firmographic key outside the held-out set: domain, not the person."""
    inputs = {r["input_id"]: r for r in read_csv(paths.datasets() / cfg["tasks"]["W1"]["input"])[1]}
    truth = read_csv(paths.datasets() / "w1-firmographics-truth.csv")[1]
    held = holdout_ids(inputs, cfg)
    rows = {}
    for g in truth:
        if g["input_id"] in inputs and g["input_id"] not in held:
            rows.setdefault(inputs[g["input_id"]]["company_domain"],
                            [inputs[g["input_id"]]["company_domain"], g["true_employee_count"], g["true_industry"], g["true_hq_country"]])
    return ["company_domain", "true_employee_count", "true_industry", "true_hq_country"], list(rows.values())


PUBLIC_EXPORTS = {"w1-firmographics-public": export_firmographics}
