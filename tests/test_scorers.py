"""W1 scorer tests on throwaway fixture data (example.com). Run: python3 -I -m unittest discover -s tests"""
import csv
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ["BENCH_REPO"] = str(REPO)
try:
    import benchkit  # noqa: F401
except ImportError:
    sys.path.insert(0, str(REPO.parent / "benchkit"))

from benchkit import artifacts, cli, costs, paths, runs, sanity, summary  # noqa: E402

INPUT = [["1", "A", "One", "a.example.com", "smb", "na"],
         ["2", "B", "Two", "b.example.com", "mid", "emea"],
         ["3", "C", "Three", "c.example.com", "ent", "apac"],
         ["4", "D", "Four", "d.example.com", "smb", "emea"]]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class W1Test(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        cfg = json.loads((REPO / "config" / "bench.json").read_text())
        cfg["tasks"]["W1"]["rows"] = 4
        (self.root / "cfg.json").write_text(json.dumps(cfg))
        os.environ["BENCH_ROOT"] = str(self.root)
        os.environ["BENCH_CONFIG"] = str(self.root / "cfg.json")
        # Fixture overlay: real names and prices live in the gitignored private/platforms.json.
        paths.write_json(paths.platform_overlay(), {"platforms": {"provider_b": {
            "name": "Fixturevendor", "unit_prices": {"credits": 0.016}}}})
        self.cfg = paths.load_config()
        ds = paths.datasets()
        write_csv(ds / "w1-input.csv", ["input_id", "first_name", "last_name", "company_domain", "segment_size", "segment_region"], INPUT)
        write_csv(ds / "w1-firmographics-truth.csv", ["input_id", "true_employee_count", "true_industry", "true_hq_country"],
                  [["1", "30", "Software", "US"], ["2", "300", "Financial services", "GB"]])

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("BENCH_ROOT", "BENCH_CONFIG"):
            os.environ.pop(k, None)

    def test_w1_end_to_end(self):
        r = runs.new_run(self.cfg, "W1", "provider_b", "agent", "agent-x", "agent", "self-serve monthly", 1)
        rid = r["run_id"]
        write_csv(runs.run_dir(rid) / "output" / "output.csv", self.cfg["tasks"]["W1"]["output_columns"],
                  [["1", "a@a.example.com", "+15550001", "A Inc", "25", "Computer Software", "us"],
                   ["2", "b@b.example.com", "", "B Ltd", "1,200", "Banking", "GB"],
                   ["3", "c@c.example.com", "", "", "", "Widgets", ""],
                   ["4", "d@gmail.example", "", "", "", "", ""]])
        write_csv(self.root / "zb.csv", ["email", "status"],
                  [["a@a.example.com", "valid"], ["b@b.example.com", "valid"], ["c@c.example.com", "invalid"],
                   ["d@gmail.example", "valid"]])
        write_csv(paths.datasets() / "w1-email-gold.csv", ["input_id", "known_email", "known_phone", "source_url"],
                  [["1", "a@a.example.com", "+1 555 0001", "https://a.example.com/team"],
                   ["2", "bea@b.example.com", "", "https://b.example.com/about"]])
        write_csv(self.root / "ph.csv", ["phone", "status"], [["+15550001", "mobile"]])
        cli.main(["verify", rid, "--mode", "import", "--email-results", str(self.root / "zb.csv"),
                  "--phone-results", str(self.root / "ph.csv")])
        cli.main(["score", rid])
        s = runs.load(rid)["score"]
        m = s["metrics"]
        self.assertEqual(s["accepted_records"], 2)
        self.assertEqual(m["email_fill_rate"], 1.0)
        self.assertEqual(m["off_domain_valid_emails"], 1)
        self.assertEqual((m["gold_email_precision"], m["gold_email_wrong"]), (0.5, 1))
        self.assertEqual((m["industry_accuracy"], m["country_accuracy"], m["band_accuracy"]), (1.0, 1.0, 0.5))
        self.assertEqual(m["verified_email_rate"], 0.5)
        self.assertEqual(m["verified_email_rate_smb"], 0.5)
        self.assertEqual(m["verified_email_rate_apac"], 0.0)
        self.assertEqual(m["valid_phone_rate"], 0.25)
        self.assertEqual(m["firmographic_accuracy"], 0.5)  # row 2 is in the wrong employee band
        self.assertEqual(s["proposed_status"], "Pass")
        runs.set_usage(rid, before=1000, after=990)
        self.assertAlmostEqual(costs.run_costs(self.cfg, runs.load(rid))["cost_per_accepted_record_usd"], 0.08)
        _, summ, _ = summary.write_all(self.cfg)
        self.assertEqual(summ[0]["verified_email_rate_median"], 0.5)
        self.assertEqual(summary.check_anonymized(self.cfg), [])

    def test_band_blank_and_unknown_key_rows(self):
        from benchkit import scoring
        sc = scoring.plugin()
        self.assertIsNone(sc.band("", [10, 50]))
        self.assertIsNone(sc.band("inf", [10, 50]))
        write_csv(paths.datasets() / "w1-firmographics-truth.csv", ["input_id", "true_employee_count", "true_industry", "true_hq_country"],
                  [["1", "", "unknown", "US"], ["2", "300", "Financial services", "GB"]])
        r = runs.new_run(self.cfg, "W1", "provider_b", "agent", "agent-x", "agent", "self-serve monthly")
        write_csv(runs.run_dir(r["run_id"]) / "output" / "output.csv", self.cfg["tasks"]["W1"]["output_columns"],
                  [["1", "", "", "", "", "", "US"], ["2", "", "", "", "", "Banking", "GB"],
                   ["3", "", "", "", "", "", ""], ["4", "", "", "", "", "", ""]])
        write_csv(self.root / "zb.csv", ["email", "status"], [["x@example.com", "valid"]])
        cli.main(["verify", r["run_id"], "--mode", "import", "--email-results", str(self.root / "zb.csv")])
        cli.main(["score", r["run_id"]])
        m = runs.load(r["run_id"])["score"]["metrics"]
        # Row 1: blank band and unknown industry aren't scored; its country is. Row 2: band missed.
        self.assertEqual((m["band_accuracy"], m["industry_accuracy"], m["country_accuracy"]), (0.0, 1.0, 1.0))
        self.assertEqual((m["firmographic_sample"], m["firmographic_accuracy"]), (1, 0.0))

    def test_audit_passes_with_routine_id_in_url(self):
        env = {"CLAY_API_KEY": "clay-key-abcdef", "CLAY_ROUTINE_ID_WATERFALL": "rt_routine_123456"}
        with unittest.mock.patch.dict(os.environ, env):
            r = runs.new_run(self.cfg, "W1", "clay", "script", "s", "script", "self-serve monthly", endpoint="clay_waterfall")
            d = runs.run_dir(r["run_id"])
            paths.write_json(d / "audit" / "1.json", {"request": {"url": "https://api.clay.com/public/v0/routines/rt_routine_123456/run",
                                                                  "headers": {"clay-api-key": "***REDACTED***"}}})
            runs.record(r["run_id"], {"failure_category": "setup"}, status="Void")
            cli.main(["manifest"])
            self.assertEqual(artifacts.audit(self.cfg), [])

    def test_sanity_oracle_and_public_export(self):
        write_csv(paths.datasets() / "w1-email-gold.csv", ["input_id", "known_email", "known_phone", "source_url"],
                  [["1", "a@a.example.com", "", "https://a.example.com/team"]])
        rows = {(t, c): (ok, d) for t, c, ok, d in sanity.run_sanity(self.cfg)}
        self.assertEqual(rows[("W1", "oracle")][0], True, rows[("W1", "oracle")])
        self.assertEqual(rows[("W1", "empty")][0], True)
        header, out = sys.modules["bench_scorers"].export_firmographics(dict(self.cfg, holdout={"share": 0}))
        self.assertEqual(header[0], "company_domain")
        self.assertEqual(len(out), 2)
        self.assertFalse(any("@" in v for row in out for v in row))

    def test_vertical_startup_agency_cuts(self):
        cols = ["input_id", "first_name", "last_name", "company_domain", "segment_size", "segment_region",
                "segment_vertical", "segment_startup", "segment_agency"]
        write_csv(paths.datasets() / "w1-input.csv", cols,
                  [["1", "A", "One", "a.example.com", "smb", "na", "Software", "Y", "N"],
                   ["2", "B", "Two", "b.example.com", "mid", "emea", "Marketing and media", "N", "Y"],
                   ["3", "C", "Three", "c.example.com", "ent", "na", "Software", "N", "N"],
                   ["4", "D", "Four", "d.example.com", "smb", "emea", "Marketing and media", "N", "Y"]])
        r = runs.new_run(self.cfg, "W1", "provider_b", "agent", "agent-x", "agent", "self-serve monthly")
        write_csv(runs.run_dir(r["run_id"]) / "output" / "output.csv", self.cfg["tasks"]["W1"]["output_columns"],
                  [["1", "a@a.example.com", "", "", "", "", ""], ["2", "b@b.example.com", "", "", "", "", ""],
                   ["3", "", "", "", "", "", ""], ["4", "", "", "", "", "", ""]])
        write_csv(self.root / "zb.csv", ["email", "status"], [["a@a.example.com", "valid"], ["b@b.example.com", "valid"]])
        cli.main(["verify", r["run_id"], "--mode", "import", "--email-results", str(self.root / "zb.csv")])
        cli.main(["score", r["run_id"]])
        m = runs.load(r["run_id"])["score"]["metrics"]
        self.assertEqual((m["verified_email_rate_vertical_software"], m["verified_email_rate_vertical_marketing_and_media"]), (0.5, 0.5))
        self.assertEqual((m["verified_email_rate_startup_y"], m["verified_email_rate_agency_y"], m["verified_email_rate_na"]), (1.0, 0.5, 0.5))
        self.assertEqual((m["n_vertical_software"], m["n_agency_y"]), (2, 2))

    def test_missing_ids_fail(self):
        r = runs.new_run(self.cfg, "W1", "clay", "agent", "agent-x", "agent", "self-serve monthly")
        write_csv(runs.run_dir(r["run_id"]) / "output" / "output.csv", self.cfg["tasks"]["W1"]["output_columns"],
                  [["1", "", "", "", "", "", ""]])
        write_csv(self.root / "zb.csv", ["email", "status"], [["x@example.com", "valid"]])
        cli.main(["verify", r["run_id"], "--mode", "import", "--email-results", str(self.root / "zb.csv")])
        cli.main(["score", r["run_id"]])
        self.assertEqual(runs.load(r["run_id"])["score"]["proposed_status"], "Fail")


if __name__ == "__main__":
    unittest.main()
