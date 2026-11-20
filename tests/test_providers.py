"""Adapter parsing tests with mocked vendor responses (no network, no credits)."""
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
os.environ["BENCH_REPO"] = str(REPO)
try:
    import benchkit  # noqa: F401
except ImportError:
    sys.path.insert(0, str(REPO.parent / "benchkit"))

from benchkit import adapters  # noqa: E402

ROW = {"input_id": "1", "first_name": "Ann", "last_name": "Lee", "company_domain": "a.example.com"}


class ProviderTest(unittest.TestCase):
    def setUp(self):
        self.reg = adapters.registry()

    def test_public_roster_is_clay_only(self):
        # The Provider A and B adapters are anonymized and not published.
        self.assertEqual(list(sys.modules["bench_providers"].ADAPTERS), ["clay_waterfall", "clay_single"])

    ENV = {"CLAY_API_KEY": "c", "CLAY_ROUTINE_ID_COMPANY": "function:t_co", "CLAY_ROUTINE_ID_LINKEDIN": "function:t_li",
           "CLAY_ROUTINE_ID_WATERFALL": "function:t_we", "CLAY_ROUTINE_ID_PHONE_WATERFALL": "function:t_ph",
           "CLAY_ROUTINE_ID_SINGLE": "function:t_fm", "CLAY_ROUTINE_ID_PHONE_SINGLE": "function:t_fo"}
    RESULTS = {"t_co": {"Enrich Company": {"name": "Acme", "employee_count": 120, "industry": "Software", "country": "US"}},
               "t_we": {"Work Email": "ann@a.example.com"}, "t_fm": {"Work Email": "ann@a.example.com"},
               "t_li": {"LinkedIn URL": "linkedin.com/in/annlee"},   # as Clay returns it: no scheme
               "t_ph": {"Mobile Phone": "+1 415 555 0100"}, "t_fo": {"Mobile Phone": "+1 415 555 0100"}}

    def fake_clay(self, bodies, fail=()):
        runs, polled = {}, {}

        def fake(method, url, headers=None, body=None):
            if method == "POST":
                rt = url.split("function:")[1].split("/")[0]
                bodies[rt] = body["items"][0]["inputs"]
                runs[f"run-{rt}"] = rt
                return 202, {"routine_run_id": f"run-{rt}", "status": "in_progress"}, 10.0, {}
            rt = runs.get(url.split("/run/")[1].split("/")[0], url.split("/run/run-")[1].split("/")[0])
            if not polled.setdefault(rt, False):
                polled[rt] = True   # first poll: still running, as Clay answers it
                return 202, {"status": "in_progress", "total": 1, "finished": 0, "data": []}, 5.0, {}
            if rt in fail:
                return 200, {"status": "processing_failed", "error": {"message": "x"}}, 5.0, {}
            return 200, {"status": "complete", "data": [{"id": "1", "status": "complete", "result": self.RESULTS[rt]}]}, 5.0, {}
        return fake

    def run_clay(self, name, journal, fail=()):
        bodies, saved = {}, {}
        with mock.patch.dict(os.environ, self.ENV), mock.patch("bench_providers.clay.http_json", side_effect=self.fake_clay(bodies, fail)), \
                mock.patch("bench_providers.clay.POST_PAUSE_S", 0), mock.patch("bench_providers.clay.POLL_S", 0):
            self.reg[name].enrich_batch([ROW], saved.__setitem__, journal)
        return bodies, saved

    def test_clay_waterfall_chain_sends_exact_inputs(self):
        journal = {}
        bodies, saved = self.run_clay("clay_waterfall", journal)
        f = saved["1"]["fields"]
        self.assertEqual((f["email"], f["phone"], f["company_name"], f["employee_count"]), ("ann@a.example.com", "+1 415 555 0100", "Acme", "120"))
        self.assertEqual(bodies["t_co"], {"Company Identifier": "a.example.com"})
        self.assertEqual(bodies["t_we"], {"Full Name": "Ann Lee", "Company Domain": "a.example.com", "Company Name": "Acme"})
        self.assertEqual(bodies["t_li"], {"Full name": "Ann Lee", "Company name": "Acme", "Company domain": "a.example.com"})
        self.assertEqual(bodies["t_ph"]["Social Profile URL"], "https://linkedin.com/in/annlee")
        self.assertEqual(sorted(journal), ["company:1", "email:1", "linkedin:1", "phone:1"])

    def test_clay_resume_polls_and_never_restarts(self):
        journal = {k: f"run-{v}" for k, v in {"company:1": "t_co", "email:1": "t_we", "linkedin:1": "t_li", "phone:1": "t_ph"}.items()}
        bodies, saved = self.run_clay("clay_waterfall", journal)
        self.assertEqual(bodies, {})   # nothing started (paid for) again
        self.assertEqual(saved["1"]["fields"]["phone"], "+1 415 555 0100")

    def test_clay_single_sends_only_its_inputs_and_survives_a_failed_company_lookup(self):
        bodies, saved = self.run_clay("clay_single", {}, fail=("t_co",))
        self.assertEqual(bodies["t_fm"], {"Full Name": "Ann Lee", "Company Domain": "a.example.com"})
        self.assertEqual(bodies["t_li"]["Company name"], "a.example.com")   # company name falls back to the domain
        self.assertEqual(bodies["t_fo"], {"Social Profile URL": "https://linkedin.com/in/annlee"})
        self.assertTrue(saved["1"]["ok"])

    def test_country_names_become_codes(self):
        from bench_providers.common import fields
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual([fields(hq_country=c)["hq_country"] for c in ("UNITED STATES", "united kingdom", "US", "Atlantis", "Atlantis")],
                             ["US", "GB", "US", "ATLANTIS", "ATLANTIS"])
        self.assertEqual(err.getvalue().count("'ATLANTIS'"), 1)   # an unmapped country is logged, once

    def test_clay_latency_is_wall_time_and_unknown_on_resume(self):
        _, saved = self.run_clay("clay_waterfall", {})
        self.assertIsNotNone(saved["1"]["latency_ms"])
        journal = {k: f"run-{v}" for k, v in {"company:1": "t_co", "email:1": "t_we", "linkedin:1": "t_li", "phone:1": "t_ph"}.items()}
        _, saved = self.run_clay("clay_waterfall", journal)
        self.assertIsNone(saved["1"]["latency_ms"])   # resumed: start time unknown, so not counted in the median

    def test_clay_no_linkedin_means_no_phone_step(self):
        self.RESULTS = dict(self.RESULTS, t_li={})
        bodies, saved = self.run_clay("clay_waterfall", {})
        self.assertNotIn("t_ph", bodies)
        self.assertEqual(saved["1"]["fields"]["phone"], "")


if __name__ == "__main__":
    unittest.main()
